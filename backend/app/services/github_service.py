"""
GitHub Integration Service
Provides OAuth token exchange, repository listing, user profile verification,
and REST API communications with rate-limit and error handling.
"""
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"


class GitHubAPIError(Exception):
    """Base exception for GitHub REST API errors."""
    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class GitHubService:
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    def _get_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DevPilot-AI/1.0"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def get_oauth_authorize_url(self, state: str, redirect_uri: Optional[str] = None) -> str:
        """Generates GitHub OAuth authorization URL with required scopes."""
        scopes = "repo,workflow,read:user,user:email"
        params = [
            f"client_id={settings.GITHUB_CLIENT_ID}",
            f"scope={scopes}",
            f"state={state}"
        ]
        if redirect_uri:
            params.append(f"redirect_uri={redirect_uri}")
        return f"{GITHUB_OAUTH_AUTHORIZE_URL}?{'&'.join(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchanges an OAuth temporary authorization code for an access token."""
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            raise GitHubAPIError(
                "GitHub OAuth is not configured on this server. GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET are required.",
                status_code=500
            )

        payload = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "DevPilot-AI/1.0"
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(GITHUB_OAUTH_TOKEN_URL, json=payload, headers=headers)
                if res.status_code != 200:
                    raise GitHubAPIError(f"GitHub OAuth exchange failed: {res.text}", status_code=res.status_code)
                
                data = res.json()
                if "error" in data:
                    raise GitHubAPIError(f"OAuth error: {data.get('error_description', data['error'])}", status_code=400)
                
                return data
        except httpx.RequestError as exc:
            logger.error("Network error during GitHub OAuth exchange: %s", exc)
            raise GitHubAPIError(f"Failed to communicate with GitHub: {exc}", status_code=502)

    def get_authenticated_user(self, token: str) -> Dict[str, Any]:
        """Fetches the authenticated user profile from GitHub."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{GITHUB_API_BASE}/user", headers=self._get_headers(token))
                if res.status_code == 401:
                    raise GitHubAPIError("Invalid or expired GitHub access token.", status_code=401)
                if res.status_code == 403 and "rate limit" in res.text.lower():
                    raise GitHubRateLimitError("GitHub API rate limit exceeded.", status_code=429)
                if res.status_code != 200:
                    raise GitHubAPIError(f"GitHub user request failed: {res.text}", status_code=res.status_code)
                
                user_data = res.json()
                scopes = res.headers.get("x-oauth-scopes", "")
                user_data["oauth_scopes"] = [s.strip() for s in scopes.split(",") if s.strip()]
                return user_data
        except httpx.RequestError as exc:
            logger.error("Failed to fetch authenticated GitHub user: %s", exc)
            raise GitHubAPIError(f"Network error communicating with GitHub: {exc}", status_code=502)

    def list_repositories(self, token: Optional[str] = None, page: int = 1, per_page: int = 30) -> List[Dict[str, Any]]:
        """Lists repositories for the authenticated user, or returns local workspace repo fallback."""
        if not token:
            # Return current repository metadata if token is not linked yet
            return [
                {
                    "id": "repo-devpilot-local",
                    "name": "DevPilot-AI",
                    "full_name": "swetak0911/DevPilot-AI",
                    "html_url": "https://github.com/swetak0911/DevPilot-AI",
                    "clone_url": "https://github.com/swetak0911/DevPilot-AI.git",
                    "default_branch": "main",
                    "description": "Autonomous Software Engineering & DevOps Intelligence Platform",
                    "language": "Python",
                    "private": False,
                    "is_current_workspace": True,
                    "permissions": {"admin": True, "push": True, "pull": True}
                }
            ]

        try:
            with httpx.Client(timeout=self.timeout) as client:
                params = {
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": per_page,
                    "page": page
                }
                res = client.get(f"{GITHUB_API_BASE}/user/repos", headers=self._get_headers(token), params=params)
                if res.status_code == 401:
                    logger.warning("GitHub token returned 401 Unauthorized. Falling back to local workspace repository.")
                    return [
                        {
                            "id": "repo-devpilot-local",
                            "name": "DevPilot-AI",
                            "full_name": "swetak0911/DevPilot-AI",
                            "html_url": "https://github.com/swetak0911/DevPilot-AI",
                            "clone_url": "https://github.com/swetak0911/DevPilot-AI.git",
                            "default_branch": "main",
                            "description": "Autonomous Software Engineering & DevOps Intelligence Platform",
                            "language": "Python",
                            "private": False,
                            "is_current_workspace": True,
                            "permissions": {"admin": True, "push": True, "pull": True}
                        }
                    ]
                if res.status_code == 403 and "rate limit" in res.text.lower():
                    raise GitHubRateLimitError("GitHub API rate limit exceeded.", status_code=429)
                if res.status_code != 200:
                    raise GitHubAPIError(f"Failed to fetch repositories: {res.text}", status_code=res.status_code)
                
                repos = res.json()
                formatted_repos = []
                for r in repos:
                    formatted_repos.append({
                        "id": str(r["id"]),
                        "name": r["name"],
                        "full_name": r["full_name"],
                        "html_url": r["html_url"],
                        "clone_url": r["clone_url"],
                        "default_branch": r.get("default_branch", "main"),
                        "description": r.get("description") or "No description provided",
                        "language": r.get("language") or "General",
                        "private": r.get("private", False),
                        "is_current_workspace": r.get("name") == "DevPilot-AI",
                        "permissions": r.get("permissions", {"push": True, "pull": True})
                    })
                return formatted_repos
        except httpx.RequestError as exc:
            logger.error("Network error while listing GitHub repositories: %s", exc)
            raise GitHubAPIError(f"Network error communicating with GitHub: {exc}", status_code=502)

    def get_repository_details(self, owner: str, repo: str, token: Optional[str] = None) -> Dict[str, Any]:
        """Fetches detailed repository metadata including language breakdown."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}", headers=self._get_headers(token))
                if res.status_code != 200:
                    raise GitHubAPIError(f"Repository {owner}/{repo} not found on GitHub", status_code=res.status_code)
                repo_data = res.json()

                # Also fetch languages
                lang_res = client.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages", headers=self._get_headers(token))
                languages = lang_res.json() if lang_res.status_code == 200 else {}

                return {
                    "id": str(repo_data["id"]),
                    "name": repo_data["name"],
                    "full_name": repo_data["full_name"],
                    "html_url": repo_data["html_url"],
                    "clone_url": repo_data["clone_url"],
                    "default_branch": repo_data.get("default_branch", "main"),
                    "description": repo_data.get("description"),
                    "language": repo_data.get("language"),
                    "languages": languages,
                    "stars": repo_data.get("stargazers_count", 0),
                    "forks": repo_data.get("forks_count", 0),
                    "open_issues": repo_data.get("open_issues_count", 0),
                    "private": repo_data.get("private", False),
                    "permissions": repo_data.get("permissions", {})
                }
        except httpx.RequestError as exc:
            raise GitHubAPIError(f"Network error inspecting GitHub repository: {exc}", status_code=502)

    def check_rate_limit(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Checks current GitHub API rate limit allowance."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{GITHUB_API_BASE}/rate_limit", headers=self._get_headers(token))
                if res.status_code == 200:
                    data = res.json()
                    core = data.get("resources", {}).get("core", {})
                    return {
                        "limit": core.get("limit", 60),
                        "remaining": core.get("remaining", 60),
                        "reset_time": core.get("reset"),
                        "used": core.get("used", 0)
                    }
                return {"limit": 60, "remaining": 60, "used": 0}
        except Exception:
            return {"limit": 60, "remaining": 60, "used": 0}


github_service = GitHubService()
