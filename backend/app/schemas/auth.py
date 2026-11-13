"""Authentication Pydantic Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# Graceful fallback if email-validator is not yet installed
try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr
except ImportError:
    EmailStr = str  # fallback to standard str if email-validator is pending install


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class GitHubStatusResponse(BaseModel):
    is_connected: bool
    github_username: Optional[str] = None
    github_avatar_url: Optional[str] = None
    scopes: List[str] = []
    connected_at: Optional[datetime] = None
    rate_limit: Optional[dict] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_github_connected: bool = False
    github_connection: Optional[GitHubStatusResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
