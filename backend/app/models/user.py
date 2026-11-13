"""User and GitHub Authentication Models."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    github_connection = relationship("GitHubConnection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class GitHubConnection(Base):
    __tablename__ = "github_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    github_user_id = Column(String(100), nullable=True)
    github_username = Column(String(100), nullable=False)
    github_avatar_url = Column(String(512), nullable=True)
    access_token = Column(Text, nullable=False)  # stored encrypted with HMAC verification
    token_scope = Column(String(255), nullable=True)
    token_type = Column(String(50), default="bearer", nullable=False)
    connected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_synced_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="github_connection")

    def get_decrypted_token(self) -> str:
        """Returns the decrypted plaintext token for authorized API requests."""
        from app.core.security import decrypt_token
        return decrypt_token(self.access_token)

    def set_encrypted_token(self, plain_token: str) -> None:
        """Encrypts and sets the access token."""
        from app.core.security import encrypt_token
        self.access_token = encrypt_token(plain_token)
