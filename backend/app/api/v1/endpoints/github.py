"""GitHub Integration Endpoints."""
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, GitHubConnection
from app.models.repository import Repository
from app.models.audit import AuditLog
from app.services.github_service import github_service, GitHubAPIError, GitHubRateLimitError
from app.services.auth_service import auth_service
from app.schemas.github import (
    GitHubConnectPAT, GitHubOAuthAuthorizeResponse, GitHubOAuthCallback,
    GitHubRepositoryItem, GitHubSelectRepoRequest
)
from app.schemas.auth import GitHubStatusResponse
from app.schemas.repository import RepositoryResponse

router = APIRouter(prefix="/github", tags=["GitHub Integration"])


@router.get("/authorize-url", response_model=GitHubOAuthAuthorizeResponse)
def get_github_authorize_url():
    """Generates a secure GitHub OAuth authorization URL with a unique CSRF state parameter."""
    state = str(uuid.uuid4())
    url = github_service.get_oauth_authorize_url(state=state)
    return GitHubOAuthAuthorizeResponse(authorize_url=url, state=state)


@router.post("/callback", response_model=GitHubStatusResponse)
def handle_github_oauth_callback(
    payload: GitHubOAuthCallback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Exchanges OAuth code for an access token, verifies account, and saves encrypted connection."""
    try:
        token_data = github_service.exchange_code_for_token(payload.code)
        access_token = token_data["access_token"]
        conn = auth_service.link_github_token(db=db, user=current_user, token=access_token)
        
        scopes = [s.strip() for s in (conn.token_scope or "").split(",") if s.strip()]
        return GitHubStatusResponse(
            is_connected=True,
            github_username=conn.github_username,
            github_avatar_url=conn.github_avatar_url,
            scopes=scopes,
            connected_at=conn.connected_at
        )
    except GitHubAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/connect", response_model=GitHubStatusResponse)
def connect_github_pat(
    payload: GitHubConnectPAT,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stores GitHub Personal Access Token or OAuth token encrypted with verification."""
    conn = auth_service.link_github_token(
        db=db,
        user=current_user,
        token=payload.access_token,
        username_override=payload.github_username
    )
    scopes = [s.strip() for s in (conn.token_scope or "").split(",") if s.strip()]
    return GitHubStatusResponse(
        is_connected=True,
        github_username=conn.github_username,
        github_avatar_url=conn.github_avatar_url,
        scopes=scopes,
        connected_at=conn.connected_at
    )


@router.get("/status", response_model=GitHubStatusResponse)
def get_github_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the current user's GitHub connection status and API rate limits."""
    conn = current_user.github_connection
    if not conn:
        return GitHubStatusResponse(is_connected=False)

    plain_token = conn.get_decrypted_token()
    rate_limit = github_service.check_rate_limit(plain_token)
    scopes = [s.strip() for s in (conn.token_scope or "").split(",") if s.strip()]

    return GitHubStatusResponse(
        is_connected=True,
        github_username=conn.github_username,
        github_avatar_url=conn.github_avatar_url,
        scopes=scopes,
        connected_at=conn.connected_at,
        rate_limit=rate_limit
    )


@router.delete("/disconnect")
def disconnect_github(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Securely unlinks and deletes stored GitHub credentials."""
    auth_service.unlink_github_account(db=db, user=current_user)
    return {"message": "GitHub account disconnected successfully."}


@router.get("/repositories", response_model=List[GitHubRepositoryItem])
def list_github_repositories(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Retrieves live repositories from the connected GitHub account via GitHub REST API."""
    token = current_user.github_connection.get_decrypted_token() if current_user.github_connection else None
    try:
        repos = github_service.list_repositories(token=token, page=page, per_page=per_page)
        return repos
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except GitHubAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/repositories/select", response_model=RepositoryResponse)
def select_and_import_repository(
    payload: GitHubSelectRepoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Selects a GitHub repository to be managed by DevPilot AI."""
    existing = db.query(Repository).filter(Repository.full_name == payload.full_name).first()
    if existing:
        return existing

    parts = payload.full_name.split("/")
    repo_name = parts[-1] if len(parts) >= 1 else "repository"
    html_url = f"https://github.com/{payload.full_name}"

    repo = Repository(
        name=repo_name,
        full_name=payload.full_name,
        html_url=html_url,
        clone_url=payload.clone_url,
        default_branch=payload.default_branch,
        description=payload.description or "Imported GitHub repository",
        primary_language=payload.language or "General",
        detected_frameworks=["FastAPI", "React", "Docker"],
        is_indexed=False
    )
    db.add(repo)

    audit = AuditLog(
        user_id=current_user.id,
        action="REPOSITORY_IMPORTED",
        resource_type="Repository",
        resource_id=repo.id,
        details={"full_name": payload.full_name}
    )
    db.add(audit)
    db.commit()
    db.refresh(repo)
    return repo
