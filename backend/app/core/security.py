"""
DevPilot AI - Security and Cryptography Utilities
Handles password hashing, JWT creation & decoding, and HMAC-authenticated token encryption.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import os
import hmac
import hashlib
import base64
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Authenticated AES-GCM encryption import with fallback
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_AESGCM = True
except ImportError:
    AESGCM = None
    HAS_AESGCM = False

# JWT library import with fallback
try:
    from jose import jwt, JWTError
except ImportError:
    try:
        import jwt
        JWTError = Exception
    except ImportError:
        jwt = None
        JWTError = Exception

# Password hashing configuration with standard library fallback
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
except Exception:
    try:
        import bcrypt

        def hash_password(password: str) -> str:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        def verify_password(plain_password: str, hashed_password: str) -> bool:
            try:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
    except Exception:
        # Zero-dependency standard library hashlib PBKDF2-HMAC fallback
        def hash_password(password: str) -> str:
            salt = os.urandom(16).hex()
            key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
            return f"pbkdf2:{salt}:{key.hex()}"

        def verify_password(plain_password: str, hashed_password: str) -> bool:
            try:
                if hashed_password.startswith("pbkdf2:"):
                    parts = hashed_password.split(":")
                    if len(parts) == 3:
                        salt = parts[1]
                        expected_hex = parts[2]
                        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
                        return hmac.compare_digest(key.hex(), expected_hex)
                env = (getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
                if env in {"production", "prod"}:
                    logger.error("Insecure unsalted password hash rejected in production environment.")
                    return False
                logger.warning("Verifying legacy unsalted hash in non-production environment.")
                expected = hashlib.sha256((plain_password + settings.SECRET_KEY).encode()).hexdigest()
                return hmac.compare_digest(expected, hashed_password)
            except Exception:
                return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    if jwt is not None:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    env = (getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
    if env in {"production", "prod"}:
        raise RuntimeError("JWT library (python-jose or PyJWT) is required for token generation in production.")
    # Minimal fallback token if jwt module is not installed in development
    token_raw = f"{to_encode['sub']}:{int(expire.timestamp())}"
    sig = hmac.new(settings.SECRET_KEY.encode(), token_raw.encode(), hashlib.sha256).hexdigest()
    return f"devpilot.{base64.urlsafe_b64encode(token_raw.encode()).decode()}.{sig}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a signed JWT token."""
    if not token:
        return None
    if jwt is not None:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except Exception:
            pass

    # Fallback decoder
    if token.startswith("devpilot."):
        parts = token.split(".")
        if len(parts) == 3:
            raw = base64.urlsafe_b64decode(parts[1].encode()).decode()
            expected_sig = hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(parts[2], expected_sig):
                sub, exp = raw.split(":")
                if int(exp) >= int(datetime.now(timezone.utc).timestamp()):
                    return {"sub": sub, "exp": int(exp)}
    return None


def _get_encryption_key() -> bytes:
    """Derives a deterministic 256-bit (32-byte) key from settings.SECRET_KEY."""
    if not settings.SECRET_KEY:
        raise ValueError("Encryption configuration error: settings.SECRET_KEY is empty")
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def encrypt_token(token: str) -> str:
    """
    Encrypts sensitive OAuth tokens with AES-256-GCM authenticated encryption.
    Produces ciphertext prefixed with 'enc:v2:' containing a 12-byte nonce,
    ciphertext, and a 16-byte GCM authentication tag.
    """
    if not token:
        return ""

    key = _get_encryption_key()
    if HAS_AESGCM and AESGCM is not None:
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # NIST standard 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, token.encode("utf-8"), None)
        payload = nonce + ciphertext
        return "enc:v2:" + base64.urlsafe_b64encode(payload).decode("utf-8")

    # In production, cryptography AES-GCM is strictly required
    env = (getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
    if env in {"production", "prod"}:
        raise RuntimeError("The cryptography library is required for AES-256-GCM token encryption in production.")

    # Non-production fallback (legacy XOR+HMAC)
    iv = os.urandom(16)
    token_bytes = token.encode("utf-8")
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(token_bytes):
        keystream.extend(hashlib.sha256(key + iv + counter.to_bytes(4, "big")).digest())
        counter += 1
    ciphertext = bytes(a ^ b for a, b in zip(token_bytes, keystream[:len(token_bytes)]))
    tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()
    payload = iv + tag + ciphertext
    return "enc:" + base64.urlsafe_b64encode(payload).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypts and validates the authentication tag of encrypted tokens.
    Supports 'enc:v2:' (AES-256-GCM) and maintains backward compatibility
    with legacy 'enc:' (HMAC-SHA256 authenticated XOR stream) tokens.
    """
    if not encrypted_token or not isinstance(encrypted_token, str):
        raise ValueError("Invalid encrypted token: token is empty or not a string")

    key = _get_encryption_key()

    if encrypted_token.startswith("enc:v2:"):
        raw_b64 = encrypted_token[len("enc:v2:"):]
        try:
            payload = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
        except Exception:
            raise ValueError("Invalid encrypted token encoding") from None

        if len(payload) < 28:  # 12-byte nonce + 16-byte minimum tag
            raise ValueError("Corrupted encrypted token: payload is too short")

        nonce = payload[:12]
        ciphertext = payload[12:]

        if HAS_AESGCM and AESGCM is not None:
            try:
                aesgcm = AESGCM(key)
                plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
                return plaintext_bytes.decode("utf-8")
            except Exception:
                raise ValueError("Token integrity verification failed or invalid decryption key") from None
        else:
            raise RuntimeError("The cryptography library is required to decrypt AES-256-GCM tokens")

    elif encrypted_token.startswith("enc:"):
        # Backward compatibility for legacy 'enc:' tokens
        logger.warning("Decrypting legacy 'enc:' token; consider migrating to 'enc:v2:'")
        raw_b64 = encrypted_token[4:]
        try:
            payload = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
        except Exception:
            raise ValueError("Invalid legacy encrypted token encoding") from None

        if len(payload) < 48:  # 16 bytes IV + 32 bytes SHA256 Tag
            raise ValueError("Legacy encrypted payload is corrupted: length less than header size")

        iv = payload[:16]
        tag = payload[16:48]
        ciphertext = payload[48:]

        expected_tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            raise ValueError("Token integrity verification failed: ciphertext has been tampered with")

        keystream = bytearray()
        counter = 0
        while len(keystream) < len(ciphertext):
            keystream.extend(hashlib.sha256(key + iv + counter.to_bytes(4, "big")).digest())
            counter += 1

        plaintext_bytes = bytes(a ^ b for a, b in zip(ciphertext, keystream[:len(ciphertext)]))
        return plaintext_bytes.decode("utf-8")

    raise ValueError("Invalid encrypted token format: missing 'enc:' or 'enc:v2:' prefix")
