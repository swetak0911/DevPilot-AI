"""
DevPilot AI - Kubernetes & Terraform Infrastructure Schemas
Defines request and response models for Kubernetes manifest generation,
OpenAPI schema validation, Pod Security Standards compliance,
Terraform HCL formatting, static security scanning, and plan approval gates.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==============================================================================
# Kubernetes Schemas
# ==============================================================================

class K8sLintIssueResponse(BaseModel):
    code: str
    severity: str
    resource_kind: str
    resource_name: str
    message: str
    remediation: str


class K8sValidateRequest(BaseModel):
    manifest_yaml: str = Field(..., description="Kubernetes YAML manifest(s) to validate")


class K8sValidateResponse(BaseModel):
    is_valid: bool
    security_score: int
    issues: List[K8sLintIssueResponse] = Field(default_factory=list)
    resources_found: List[Dict[str, str]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class K8sGenerateRequest(BaseModel):
    app_name: str = Field(default="devpilot-app")
    namespace: str = Field(default="default")
    image: Optional[str] = Field(default=None)
    tag: str = Field(default="latest")
    replicas: int = Field(default=2)
    container_port: int = Field(default=8000)
    port: Optional[int] = Field(default=None, description="Alias for container_port")
    service_port: int = Field(default=80)
    service_type: str = Field(default="ClusterIP")
    env_vars: Optional[Dict[str, str]] = Field(default=None)
    cpu_request: str = Field(default="200m")
    cpu_limit: str = Field(default="500m")
    memory_request: str = Field(default="256Mi")
    memory_limit: str = Field(default="512Mi")
    health_path: str = Field(default="/api/health")
    enable_hpa: bool = Field(default=True)
    min_replicas: int = Field(default=2)
    max_replicas: int = Field(default=10)
    enable_ingress: bool = Field(default=True)
    ingress_host: Optional[str] = Field(default=None)
    repository_id: Optional[str] = Field(default="default-repo")

    def model_post_init(self, __context: Any) -> None:
        if self.port is not None and self.container_port == 8000:
            self.container_port = self.port


class K8sGenerateResponse(BaseModel):
    deployment_yaml: str
    service_yaml: str
    configmap_yaml: str
    hpa_yaml: Optional[str] = None
    ingress_yaml: Optional[str] = None
    all_manifests_combined: str
    validation: K8sValidateResponse
    app_name: str
    namespace: str
    replicas: int


class K8sCommitRequest(BaseModel):
    repository_id: Optional[str] = Field(default="default-repo")
    branch_name: Optional[str] = Field(default="devpilot/k8s-manifests")
    manifest_yaml: str
    commit_message: Optional[str] = Field(default="chore(k8s): configure production Kubernetes manifests")


class K8sCommitResponse(BaseModel):
    success: bool
    branch_name: str
    commit_hash: str
    files_committed: List[str]
    message: str


# ==============================================================================
# Terraform Schemas
# ==============================================================================

class TerraformFmtRequest(BaseModel):
    hcl_content: str = Field(..., description="Raw Terraform / HCL code to format")


class TerraformFmtResponse(BaseModel):
    formatted_content: str
    is_formatted: bool


class TerraformFindingResponse(BaseModel):
    rule_id: str
    severity: str
    resource_type: str
    resource_name: str
    message: str
    remediation: str
    line_number: Optional[int] = None


class TerraformAnalyseRequest(BaseModel):
    repository_id: Optional[str] = Field(default="default-repo")
    directory_path: Optional[str] = Field(default="terraform")
    hcl_content: Optional[str] = Field(default=None)


class TerraformAnalyseResponse(BaseModel):
    is_valid: bool
    security_score: int
    resources_count: int
    findings: List[TerraformFindingResponse] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    plan_summary: Optional[str] = None


class TerraformPlanRequest(BaseModel):
    plan_text: Optional[str] = Field(default=None)
    plan_json: Optional[Dict[str, Any]] = Field(default=None)


class TerraformPlanResponse(BaseModel):
    to_add: int
    to_change: int
    to_destroy: int
    resources_to_create: List[str] = Field(default_factory=list)
    resources_to_modify: List[str] = Field(default_factory=list)
    resources_to_delete: List[str] = Field(default_factory=list)
    destructive_changes: bool
    destructive_reasons: List[str] = Field(default_factory=list)
    requires_human_approval: bool
    approval_status: str
    plan_summary: str
    approval_token: str


class TerraformApprovalRequest(BaseModel):
    approval_token: str
    approved: bool
    approver: str = Field(default="developer")
    comment: Optional[str] = Field(default=None)


class TerraformApprovalResponse(BaseModel):
    token: str
    approver: str
    status: str
    timestamp: float
    comment: str
