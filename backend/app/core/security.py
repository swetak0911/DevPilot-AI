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
    # Minimal fallback token if jwt module is not installed
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


def encrypt_token(token: str) -> str:
    """
    Encrypts sensitive OAuth tokens with HMAC-SHA256 authenticated symmetric encryption.
    Produces ciphertext prefixed with 'enc:'.
    """
    if not token:
        return ""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    iv = os.urandom(16)
    
    # Generate keystream via repeated SHA256 of key + iv + counter
    token_bytes = token.encode("utf-8")
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(token_bytes):
        keystream.extend(hashlib.sha256(key + iv + counter.to_bytes(4, "big")).digest())
        counter += 1
    
    # XOR cipher
    ciphertext = bytes(a ^ b for a, b in zip(token_bytes, keystream[:len(token_bytes)]))
    tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()
    
    payload = iv + tag + ciphertext
    return "enc:" + base64.urlsafe_b64encode(payload).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypts and verifies authentication tag of encrypted OAuth tokens.
    Raises Exception if data has been tampered with.
    """
    if not encrypted_token or not encrypted_token.startswith("enc:"):
        raise ValueError("Invalid encrypted token format: missing 'enc:' prefix")
    
    raw_b64 = encrypted_token[4:]
    try:
        payload = base64.urlsafe_b64decode(raw_b64.encode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Base64 decoding failed: {exc}")
    
    if len(payload) < 48:  # 16 bytes IV + 32 bytes SHA256 Tag
        raise ValueError("Encrypted payload is corrupted: length less than header size")
    
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    iv = payload[:16]
    tag = payload[16:48]
    ciphertext = payload[48:]
    
    # Authenticate tag
    expected_tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Token integrity verification failed: ciphertext has been tampered with")
    
    # Keystream decrypt
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(ciphertext):
        keystream.extend(hashlib.sha256(key + iv + counter.to_bytes(4, "big")).digest())
        counter += 1
    
    plaintext_bytes = bytes(a ^ b for a, b in zip(ciphertext, keystream[:len(ciphertext)]))
    return plaintext_bytes.decode("utf-8")
