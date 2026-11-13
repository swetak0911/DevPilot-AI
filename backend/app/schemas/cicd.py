"""CI/CD and DevOps Schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FrameworkDetectRequest(BaseModel):
    repository_id: str


class FrameworkDetectResponse(BaseModel):
    primary_language: str
    detected_frameworks: List[str]
    build_tool: str
    test_runner: str
    linter: Optional[str] = None
    has_docker: bool = False
    has_tests: bool = True
    has_linting: bool = True
    recommended_matrix: Dict[str, List[str]] = Field(default_factory=dict)
    manifest_paths: List[str] = Field(default_factory=list)


class WorkflowGenerateRequest(BaseModel):
    repository_id: str
    target_framework: Optional[str] = None
    workflow_name: str = "DevPilot Continuous Integration"
    branches: List[str] = Field(default_factory=lambda: ["main", "develop"])
    include_linting: bool = True
    include_tests: bool = True
    include_matrix: bool = False
    include_docker: bool = False
    include_services: List[str] = Field(default_factory=list)
    environment_vars: Dict[str, str] = Field(default_factory=dict)


class WorkflowGenerateResponse(BaseModel):
    workflow_yaml: str
    suggested_filename: str = ".github/workflows/devpilot-ci.yml"
    detected_language: str
    detected_framework: str
    validation_status: str  # VALID, INVALID
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    jobs_generated: List[str] = Field(default_factory=list)


class WorkflowValidateRequest(BaseModel):
    workflow_yaml: str


class WorkflowValidateResponse(BaseModel):
    is_valid: bool
    syntax_valid: bool
    schema_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    lint_issues: List[Dict[str, Any]] = Field(default_factory=list)
    jobs_detected: List[str] = Field(default_factory=list)


class WorkflowCommitRequest(BaseModel):
    repository_id: str
    workflow_yaml: str
    file_path: str = ".github/workflows/ci.yml"
    branch_name: str = "devpilot/setup-cicd"
    commit_message: str = "ci: configure automated GitHub Actions pipeline"


class WorkflowCommitResponse(BaseModel):
    success: bool
    commit_hash: str
    branch_name: str
    file_path: str
    message: str


class WorkflowDispatchTriggerRequest(BaseModel):
    repository_id: str
    workflow_name: str = "DevPilot Continuous Integration"
    branch_name: str = "main"


class WorkflowRunResponse(BaseModel):
    id: str
    repository_id: str
    github_run_id: Optional[str] = None
    workflow_name: str
    event: str
    status: str
    conclusion: Optional[str] = None
    duration_seconds: int
    commit_sha: Optional[str] = None
    branch_name: Optional[str] = "main"
    jobs_data: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    logs_summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CIAnalysisResponse(BaseModel):
    run_id: str
    workflow_name: str
    failed_job: str
    failed_step: str
    failure_category: str  # APPLICATION_CODE, DEPENDENCY, CI_CONFIG, ENVIRONMENT
    error_logs: str
    root_cause_hypothesis: str
    suggested_fix: str
    failing_file: Optional[str] = None
    failing_line: Optional[int] = None
    confidence_score: float = 0.95
    recommended_patch: Optional[str] = None


class CIRemediateRequest(BaseModel):
    run_id: str
    branch_name: Optional[str] = None
    patch: Optional[str] = None


class CIRemediateResponse(BaseModel):
    success: bool
    run_id: str
    branch_name: str
    commit_hash: str
    validation_passed: bool
    message: str


class CILogParseRequest(BaseModel):
    logs: str
    workflow_name: Optional[str] = "DevPilot CI"


class CILogParseResponse(BaseModel):
    failed_job: str
    failed_step: str
    failure_category: str
    error_message: str
    failing_file: Optional[str] = None
    failing_line: Optional[int] = None
    root_cause_hypothesis: str
    suggested_fix: str
    recommended_patch: Optional[str] = None


from app.schemas.docker import (
    DockerGenerateRequest,
    DockerGenerateResponse,
    DockerValidateRequest,
    DockerValidateResponse,
    DockerOptimizeRequest,
    DockerOptimizeResponse,
    DockerCommitRequest,
    DockerCommitResponse
)
from app.schemas.infrastructure import (
    K8sGenerateRequest,
    K8sGenerateResponse,
    K8sValidateRequest,
    K8sValidateResponse,
    K8sCommitRequest,
    K8sCommitResponse,
    TerraformAnalyseRequest,
    TerraformAnalyseResponse,
    TerraformFmtRequest,
    TerraformFmtResponse,
    TerraformPlanRequest,
    TerraformPlanResponse,
    TerraformApprovalRequest,
    TerraformApprovalResponse
)
