"""
DevPilot AI - Phase 13 Kubernetes & Terraform Infrastructure Agent Tests
Tests Kubernetes manifest synthesis, OpenAPI & Pod Security Standards validation,
Terraform HCL parsing, terraform fmt, static security linter, and plan approval gates.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, SessionLocal
from devops.k8s.manifest_generator import k8s_manifest_generator, K8sManifestSet
from devops.k8s.k8s_validator import k8s_validator, K8sValidationResult
from devops.terraform.iac_parser import iac_parser, HclParseResult
from devops.terraform.terraform_linter import terraform_linter, TerraformLintResult
from devops.terraform.plan_engine import terraform_plan_engine, PlanAnalysisResult
from app.services.infrastructure_service import infrastructure_service
from app.schemas.infrastructure import (
    K8sGenerateRequest,
    K8sValidateRequest,
    K8sCommitRequest,
    TerraformFmtRequest,
    TerraformAnalyseRequest,
    TerraformPlanRequest,
    TerraformApprovalRequest
)


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_k8s_manifest_generator():
    m_set: K8sManifestSet = k8s_manifest_generator.generate(
        app_name="devpilot-api",
        namespace="production",
        replicas=3,
        container_port=8000,
        enable_hpa=True,
        enable_ingress=True
    )

    assert m_set.app_name == "devpilot-api"
    assert m_set.namespace == "production"
    assert "kind: Deployment" in m_set.deployment_yaml
    assert "kind: Service" in m_set.service_yaml
    assert "kind: ConfigMap" in m_set.configmap_yaml
    assert "kind: HorizontalPodAutoscaler" in m_set.hpa_yaml
    assert "kind: Ingress" in m_set.ingress_yaml

    # Security & PSS checks
    assert "runAsNonRoot: true" in m_set.deployment_yaml
    assert "runAsUser: 10001" in m_set.deployment_yaml
    assert "allowPrivilegeEscalation: false" in m_set.deployment_yaml
    assert "livenessProbe:" in m_set.deployment_yaml
    assert "readinessProbe:" in m_set.deployment_yaml
    assert "resources:" in m_set.deployment_yaml


def test_k8s_validator_pss_and_schema():
    # 1. Valid generated manifest
    m_set = k8s_manifest_generator.generate(app_name="auth-service", port=8000)
    val_good: K8sValidationResult = k8s_validator.validate(m_set.all_manifests_combined)
    assert val_good.is_valid is True
    assert val_good.security_score >= 80
    assert len(val_good.resources_found) >= 3

    # 2. Insecure / invalid manifest
    insecure_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: insecure-app
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 999999
"""
    val_bad: K8sValidationResult = k8s_validator.validate(insecure_yaml)
    codes = {i.code for i in val_bad.issues}
    assert "K8S_NET_001" in codes  # Invalid port number > 65535
    assert "K8S_SEC_001" in codes  # Missing runAsNonRoot
    assert "K8S_SEC_002" in codes  # Missing requests/limits
    assert "K8S_SEC_004" in codes  # Missing probes
    assert val_bad.is_valid is False
    assert val_bad.security_score < 60


def test_terraform_iac_parser_and_fmt():
    raw_hcl = """resource "aws_s3_bucket" "b" {
bucket="my-bucket"
acl = "private"
}

provider "aws" {
region = "us-east-1"
}
"""
    parsed: HclParseResult = iac_parser.parse(raw_hcl)
    assert parsed.resource_count == 1
    assert "aws" in parsed.provider_names

    formatted = iac_parser.terraform_fmt(raw_hcl)
    assert "  bucket = \"my-bucket\"" in formatted
    assert "  acl    = \"private\"" in formatted  # '=' aligned


def test_terraform_security_linter():
    vulnerable_tf = """resource "aws_security_group" "bad_sg" {
  name = "bad-sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "public_bucket" {
  bucket = "leaky-bucket"
  acl    = "public-read"
}

resource "aws_ebs_volume" "unencrypted_vol" {
  availability_zone = "us-east-1a"
  size              = 40
  encrypted         = false
}

provider "aws" {
  region     = "us-east-1"
  secret_key = "AKIA1234567890SECRETKEY"
}
"""
    lint_res: TerraformLintResult = terraform_linter.lint(vulnerable_tf)
    rules = {f.rule_id for f in lint_res.findings}
    assert "TF_SEC_001" in rules  # SSH port 22 open to 0.0.0.0/0
    assert "TF_SEC_002" in rules  # S3 bucket public-read ACL
    assert "TF_SEC_003" in rules  # Hardcoded secret_key
    assert "TF_SEC_004" in rules  # Unencrypted EBS volume
    assert lint_res.is_valid is False
    assert lint_res.security_score < 60


def test_terraform_plan_risk_and_approval_gate():
    plan_with_destruction = """
Plan: 2 to add, 1 to change, 1 to destroy.
# aws_db_instance.postgres will be destroyed
# aws_instance.web will be created
"""
    plan_res: PlanAnalysisResult = terraform_plan_engine.analyze_plan(plan_with_destruction)
    assert plan_res.to_add == 2
    assert plan_res.to_destroy == 1
    assert plan_res.destructive_changes is True
    assert plan_res.requires_human_approval is True
    assert plan_res.approval_status == "AWAITING_APPROVAL"

    # Human-in-the-loop approval registration
    appr_token = "token-test-1234"
    rec = terraform_plan_engine.record_approval(
        approval_token=appr_token,
        approver="lead-devops",
        approved=True,
        comment="Database migration verified; destruction permitted."
    )
    assert rec["status"] == "APPROVED"
    assert rec["approver"] == "lead-devops"


def test_infra_service_git_commits(db):
    gen_req = K8sGenerateRequest(app_name="gateway-api", port=8000)
    k8s_res = infrastructure_service.generate_k8s_manifests(gen_req, db=db)
    assert k8s_res.validation.security_score >= 80

    commit_req = K8sCommitRequest(
        repository_id="default-repo",
        branch_name="devpilot/k8s-infra-test",
        manifest_yaml=k8s_res.all_manifests_combined
    )
    commit_res = infrastructure_service.commit_k8s_manifests(db, commit_req)
    assert commit_res.success is True
    assert "devpilot/k8s-infra-test" in commit_res.branch_name
    assert "k8s/manifests.yaml" in commit_res.files_committed


def test_kubernetes_and_terraform_rest_apis(client):
    # 1. POST /api/kubernetes/generate
    res_k8s_gen = client.post("/api/kubernetes/generate", json={
        "app_name": "orders-service",
        "container_port": 8080,
        "replicas": 3
    })
    assert res_k8s_gen.status_code == 200
    k8s_data = res_k8s_gen.json()
    assert "orders-service" in k8s_data["deployment_yaml"]
    assert k8s_data["validation"]["is_valid"] is True

    # 2. POST /api/kubernetes/validate
    res_k8s_val = client.post("/api/kubernetes/validate", json={
        "manifest_yaml": k8s_data["all_manifests_combined"]
    })
    assert res_k8s_val.status_code == 200
    assert res_k8s_val.json()["security_score"] >= 80

    # 3. POST /api/kubernetes/commit
    res_k8s_com = client.post("/api/kubernetes/commit", json={
        "repository_id": "default-repo",
        "branch_name": "devpilot/k8s-api-test",
        "manifest_yaml": k8s_data["all_manifests_combined"]
    })
    assert res_k8s_com.status_code == 200
    assert res_k8s_com.json()["success"] is True

    # 4. POST /api/terraform/fmt
    unformatted = 'resource "aws_s3_bucket" "test" {\nbucket="my-test-bucket"\nacl="private"\n}\n'
    res_tf_fmt = client.post("/api/terraform/fmt", json={"hcl_content": unformatted})
    assert res_tf_fmt.status_code == 200
    assert '  bucket = "my-test-bucket"' in res_tf_fmt.json()["formatted_content"]

    # 5. POST /api/terraform/analyse
    res_tf_ana = client.post("/api/terraform/analyse", json={
        "hcl_content": unformatted
    })
    assert res_tf_ana.status_code == 200
    assert "security_score" in res_tf_ana.json()

    # 6. POST /api/terraform/plan
    res_tf_plan = client.post("/api/terraform/plan", json={
        "plan_text": "Plan: 3 to add, 0 to change, 1 to destroy.\n# aws_db_instance.db will be destroyed"
    })
    assert res_tf_plan.status_code == 200
    plan_data = res_tf_plan.json()
    assert plan_data["destructive_changes"] is True
    assert "approval_token" in plan_data

    # 7. POST /api/terraform/approve
    res_tf_appr = client.post("/api/terraform/approve", json={
        "approval_token": plan_data["approval_token"],
        "approved": True,
        "approver": "security-officer"
    })
    assert res_tf_appr.status_code == 200
    assert res_tf_appr.json()["status"] == "APPROVED"
