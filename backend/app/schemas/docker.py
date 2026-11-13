"""
DevPilot AI - Docker Subsystem Schemas
Defines request and response models for Dockerfile generation,
container security linting, optimization, and git branch commits.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DockerGenerateRequest(BaseModel):
    language: Optional[str] = Field(default="python", description="Target programming language")
    framework: Optional[str] = Field(default=None, description="Target web/app framework")
    port: Optional[int] = Field(default=8000, description="Container exposed port")
    target_port: Optional[int] = Field(default=None, description="Legacy alias for port")
    multi_stage: bool = Field(default=True, description="Enable multi-stage build optimization")
    non_root: bool = Field(default=True, description="Enforce unprivileged user execution")
    base_image: Optional[str] = Field(default=None, description="Custom base image")
    env_vars: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    healthcheck: bool = Field(default=True, description="Include container healthcheck probe")
    entrypoint_cmd: Optional[str] = Field(default=None, description="Custom entrypoint or CMD command")
    custom_dockerignore_rules: Optional[List[str]] = Field(default=None, description="Extra rules for .dockerignore")
    repository_id: Optional[str] = Field(default=None, description="Repository identifier")

    def model_post_init(self, __context: Any) -> None:
        if self.target_port is not None and (self.port == 8000 or self.port is None):
            self.port = self.target_port


class DockerLintIssueResponse(BaseModel):
    code: str
    severity: str
    line_number: Optional[int]
    message: str
    suggestion: str


class DockerValidateRequest(BaseModel):
    dockerfile_content: str = Field(..., description="Raw Dockerfile content to analyze")


class DockerValidateResponse(BaseModel):
    is_valid: bool
    security_score: int
    issues: List[DockerLintIssueResponse]
    layer_count: int
    stages_detected: List[str]


class DockerGenerateResponse(BaseModel):
    dockerfile_content: str
    dockerignore_content: str
    language: str
    framework: Optional[str]
    base_image: str
    stages: List[str]
    exposed_port: int
    has_healthcheck: bool
    is_non_root: bool
    estimated_size_mb: int
    security_score: int
    recommendations: List[str]
    validation: DockerValidateResponse


class DockerOptimizeRequest(BaseModel):
    language: str = Field(default="python")
    base_image: Optional[str] = Field(default=None)
    multi_stage: bool = Field(default=True)
    image_name: Optional[str] = Field(default="devpilot-app")
    tag: Optional[str] = Field(default="latest")
    platforms: Optional[List[str]] = Field(default=None)
    port: Optional[int] = Field(default=8000)


class DockerOptimizeResponse(BaseModel):
    estimated_size_mb: int
    savings_mb: int
    savings_percentage: float
    recommendations: List[str]
    multiarch_recipe: Dict[str, Any]
    compose_snippet: str


class DockerCommitRequest(BaseModel):
    repository_id: Optional[str] = Field(default="default-repo")
    branch_name: Optional[str] = Field(default="devpilot/dockerize")
    dockerfile_content: str
    dockerignore_content: Optional[str] = None
    commit_message: Optional[str] = Field(default="chore(docker): add production multi-stage Dockerfile and .dockerignore")


class DockerCommitResponse(BaseModel):
    success: bool
    branch_name: str
    commit_hash: str
    files_committed: List[str]
    message: str
