"""Authentication Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.models.user import User
from app.services.auth_service import auth_service
from app.services.github_service import github_service
from app.schemas.auth import (
    UserRegister, UserLogin, UserUpdate, PasswordChange,
    UserResponse, TokenResponse, GitHubStatusResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _build_user_response(user: User) -> UserResponse:
    gh_status = None
    if user.github_connection:
        scopes = [s.strip() for s in (user.github_connection.token_scope or "").split(",") if s.strip()]
        gh_status = GitHubStatusResponse(
            is_connected=True,
            github_username=user.github_connection.github_username,
            github_avatar_url=user.github_connection.github_avatar_url,
            scopes=scopes,
            connected_at=user.github_connection.connected_at
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_github_connected=bool(user.github_connection),
        github_connection=gh_status,
        created_at=user.created_at
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """Registers a new developer user with hashed credentials."""
    user = auth_service.register_user(
        db=db,
        email=user_in.email,
        username=user_in.username,
        password=user_in.password,
        full_name=user_in.full_name
    )
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_build_user_response(user)
    )


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues a JWT."""
    user = auth_service.authenticate_user(db=db, email=user_in.email, password=user_in.password)
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_build_user_response(user)
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieves authenticated user profile details with GitHub link status."""
    return _build_user_response(current_user)


@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates user profile details."""
    updated = auth_service.update_profile(db=db, user=current_user, full_name=payload.full_name)
    return _build_user_response(updated)


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Securely updates user password after verifying current password."""
    auth_service.change_password(
        db=db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password
    )
    return {"message": "Password updated successfully."}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(current_user: User = Depends(get_current_user)):
    """Refreshes the active session token."""
    new_token = create_access_token({"sub": current_user.id, "email": current_user.email})
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user=_build_user_response(current_user)
    )
