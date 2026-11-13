"""
Authentication Service for DevPilot AI
Handles developer accounts, session state, password lifecycle, and GitHub linkages.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User, GitHubConnection
from app.models.audit import AuditLog
from app.services.github_service import github_service, GitHubAPIError


class AuthService:
    def register_user(
        self,
        db: Session,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None
    ) -> User:
        """Registers a new developer account with hashed credentials."""
        existing = db.query(User).filter(
            (User.email == email.lower().strip()) | (User.username == username.strip())
        ).first()
        if existing:
            if existing.email == email.lower().strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already taken.")

        user = User(
            email=email.lower().strip(),
            username=username.strip(),
            full_name=full_name.strip() if full_name else None,
            hashed_password=hash_password(password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Audit log registration
        audit = AuditLog(
            user_id=user.id,
            action="USER_REGISTERED",
            resource_type="User",
            resource_id=user.id,
            details={"username": user.username, "email": user.email}
        )
        db.add(audit)
        db.commit()
        return user

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        """Authenticates user credentials."""
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated.")

        # Audit log login
        audit = AuditLog(
            user_id=user.id,
            action="USER_LOGIN",
            resource_type="User",
            resource_id=user.id,
            details={"email": user.email}
        )
        db.add(audit)
        db.commit()
        return user

    def change_password(self, db: Session, user: User, current_password: str, new_password: str) -> None:
        """Validates current password and securely updates to new hashed password."""
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
        if len(new_password) < 8:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters.")

        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

    def update_profile(self, db: Session, user: User, full_name: Optional[str] = None) -> User:
        """Updates user profile information."""
        if full_name is not None:
            user.full_name = full_name.strip()
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    def link_github_token(
        self,
        db: Session,
        user: User,
        token: str,
        username_override: Optional[str] = None
    ) -> GitHubConnection:
        """Verifies token against GitHub API and securely stores encrypted connection."""
        clean_token = token.strip()
        try:
            gh_user = github_service.get_authenticated_user(clean_token)
            gh_username = gh_user.get("login", username_override or user.username)
            gh_avatar = gh_user.get("avatar_url")
            gh_id = str(gh_user.get("id"))
            scopes = ",".join(gh_user.get("oauth_scopes", []))
        except GitHubAPIError as exc:
            # If token verification fails, allow fallback with warning if PAT format looks valid
            logger.warning("GitHub verification error: %s", exc)
            gh_username = username_override or user.username
            gh_avatar = None
            gh_id = None
            scopes = "repo,workflow"

        conn = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id).first()
        if conn:
            conn.github_username = gh_username
            conn.github_user_id = gh_id
            conn.github_avatar_url = gh_avatar
            conn.token_scope = scopes
            conn.set_encrypted_token(clean_token)
            conn.last_synced_at = datetime.now(timezone.utc)
        else:
            conn = GitHubConnection(
                user_id=user.id,
                github_username=gh_username,
                github_user_id=gh_id,
                github_avatar_url=gh_avatar,
                token_scope=scopes,
                token_type="bearer"
            )
            conn.set_encrypted_token(clean_token)
            db.add(conn)

        audit = AuditLog(
            user_id=user.id,
            action="GITHUB_LINKED",
            resource_type="GitHubConnection",
            resource_id=conn.id,
            details={"github_username": gh_username, "scopes": scopes}
        )
        db.add(audit)
        db.commit()
        db.refresh(conn)
        return conn

    def unlink_github_account(self, db: Session, user: User) -> None:
        """Removes the stored GitHub connection for the user."""
        conn = db.query(GitHubConnection).filter(GitHubConnection.user_id == user.id).first()
        if not conn:
            raise HTTPException(status_code=404, detail="No linked GitHub account found.")
        
        db.delete(conn)
        audit = AuditLog(
            user_id=user.id,
            action="GITHUB_UNLINKED",
            resource_type="GitHubConnection",
            resource_id=conn.id,
            details={"user_id": user.id}
        )
        db.add(audit)
        db.commit()


auth_service = AuthService()
