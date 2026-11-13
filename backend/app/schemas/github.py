"""GitHub Integration Schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GitHubConnectPAT(BaseModel):
    access_token: str = Field(..., min_length=10, description="GitHub Personal Access Token or OAuth token")
    github_username: Optional[str] = None


class GitHubOAuthAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class GitHubOAuthCallback(BaseModel):
    code: str
    state: str


class GitHubRepositoryItem(BaseModel):
    id: str
    name: str
    full_name: str
    html_url: str
    clone_url: str
    default_branch: str
    description: Optional[str] = None
    language: Optional[str] = None
    private: bool = False
    is_current_workspace: bool = False
    permissions: Dict[str, bool] = {}


class GitHubSelectRepoRequest(BaseModel):
    full_name: str
    clone_url: str
    default_branch: str = "main"
    description: Optional[str] = None
    language: Optional[str] = None
