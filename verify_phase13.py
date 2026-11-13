"""
========================================================================
 DevPilot AI - Phase 13 Kubernetes & Terraform Agents Verification Suite
========================================================================
Statically and dynamically verifies Kubernetes manifest generation,
OpenAPI/PSS validation, Terraform HCL parsing, terraform fmt formatting,
static security linter (tfsec/Checkov rules), execution plan risk engine,
and Human-in-the-Loop infrastructure approval gates.
========================================================================
"""
import sys
import os
import json
from typing import Dict, Any, List

# Add workspace and backend to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

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


def run_phase13_verification() -> bool:
    print("=" * 72)
    print(" DevPilot AI - Phase 13 Kubernetes & Terraform Agents Suite")
    print("=" * 72)

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Kubernetes Manifest Generator (Deployment, Service, ConfigMap, HPA, Ingress)
        try:
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

            # Pod Security Standards (Restricted profile) checks
            assert "runAsNonRoot: true" in m_set.deployment_yaml
            assert "runAsUser: 10001" in m_set.deployment_yaml
            assert "allowPrivilegeEscalation: false" in m_set.deployment_yaml
            assert "livenessProbe:" in m_set.deployment_yaml
            assert "readinessProbe:" in m_set.deployment_yaml
            assert "resources:" in m_set.deployment_yaml

            print(f" [PASS] 1. Kubernetes Manifest Generator: OK (Deployment, Service, ConfigMap, HPA, Ingress generated with PSS Restricted compliance)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Kubernetes Manifest Generator: {type(e).__name__}: {e}")

        # Check 2: OpenAPI & Pod Security Standards (PSS) Validator
        try:
            # 2.1 Validate clean generated manifests
            val_good: K8sValidationResult = k8s_validator.validate(m_set.all_manifests_combined)
            assert val_good.is_valid is True, f"Expected valid, got issues: {val_good.issues}"
            assert val_good.security_score >= 80, f"Expected score >= 80, got {val_good.security_score}"
            assert len(val_good.resources_found) >= 3, f"Expected >= 3 resources found, got {len(val_good.resources_found)}"

            # 2.2 Detect violations in insecure manifests
            insecure_yaml = (
                "apiVersion: apps/v1\n"
                "kind: Deployment\n"
                "metadata:\n"
                "  name: bad-app\n"
                "spec:\n"
                "  replicas: 1\n"
                "  template:\n"
                "    spec:\n"
                "      containers:\n"
                "      - name: app\n"
                "        image: nginx:latest\n"
                "        ports:\n"
                "        - containerPort: 99999\n"
            )
            val_bad: K8sValidationResult = k8s_validator.validate(insecure_yaml)
            codes = {i.code for i in val_bad.issues}
            assert "K8S_NET_001" in codes, f"K8S_NET_001 not in {codes}"  # Port out of bounds
            assert "K8S_SEC_001" in codes, f"K8S_SEC_001 not in {codes}"  # Missing runAsNonRoot
            assert "K8S_SEC_002" in codes, f"K8S_SEC_002 not in {codes}"  # Missing requests/limits
            assert "K8S_SEC_004" in codes, f"K8S_SEC_004 not in {codes}"  # Missing probes
            assert val_bad.is_valid is False, f"Expected invalid, got score {val_bad.security_score}"
            assert val_bad.security_score < 60, f"Expected score < 60, got {val_bad.security_score}"

            print(f" [PASS] 2. OpenAPI & PSS Validator: OK (Flagged port bounds, root execution, and missing probes; Scored {val_good.security_score}/100 on hardened build)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. OpenAPI & PSS Validator: {type(e).__name__}: {e}")

        # Check 3: HCL IaC Parser & 'terraform fmt' Formatter
        try:
            raw_hcl = (
                'resource "aws_s3_bucket" "b" {\n'
                'bucket="my-bucket"\n'
                'acl = "private"\n'
                '}\n\n'
                'provider "aws" {\n'
                'region = "us-east-1"\n'
                '}\n'
            )
            parsed: HclParseResult = iac_parser.parse(raw_hcl)
            assert parsed.resource_count == 1, f"Expected 1 resource, got {parsed.resource_count}"
            assert "aws" in parsed.provider_names, f"Expected 'aws' in {parsed.provider_names}"

            formatted = iac_parser.terraform_fmt(raw_hcl)
            assert '  bucket = "my-bucket"' in formatted
            assert '  acl    = "private"' in formatted  # '=' aligned

            print(f" [PASS] 3. HCL IaC Parser & Formatter: OK (Parsed resources & providers; formatted indentation & aligned assignment operators)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. HCL Parser & Formatter: {type(e).__name__}: {e}")

        # Check 4: Terraform Security Linter (tfsec / Checkov rules)
        try:
            vulnerable_tf = (
                'resource "aws_security_group" "bad_sg" {\n'
                '  name = "bad-sg"\n'
                '  ingress {\n'
                '    from_port   = 22\n'
                '    to_port     = 22\n'
                '    protocol    = "tcp"\n'
                '    cidr_blocks = ["0.0.0.0/0"]\n'
                '  }\n'
                '}\n\n'
                'resource "aws_s3_bucket" "public_bucket" {\n'
                '  bucket = "leaky-bucket"\n'
                '  acl    = "public-read"\n'
                '}\n\n'
                'resource "aws_ebs_volume" "unencrypted_vol" {\n'
                '  availability_zone = "us-east-1a"\n'
                '  size              = 40\n'
                '  encrypted         = false\n'
                '}\n\n'
                'provider "aws" {\n'
                '  region     = "us-east-1"\n'
                '  secret_key = "AKIA1234567890SECRETKEY"\n'
                '}\n'
            )

            lint_res: TerraformLintResult = terraform_linter.lint(vulnerable_tf)
            rules = {f.rule_id for f in lint_res.findings}
            assert "TF_SEC_001" in rules, f"TF_SEC_001 not in {rules}"  # SSH 22 open to 0.0.0.0/0
            assert "TF_SEC_002" in rules, f"TF_SEC_002 not in {rules}"  # S3 bucket public-read ACL
            assert "TF_SEC_003" in rules, f"TF_SEC_003 not in {rules}"  # Hardcoded secret_key
            assert "TF_SEC_004" in rules, f"TF_SEC_004 not in {rules}"  # Unencrypted storage
            assert lint_res.is_valid is False
            assert lint_res.security_score < 60

            print(f" [PASS] 4. Terraform Security Linter: OK (Identified TF_SEC_001, TF_SEC_002, TF_SEC_003, TF_SEC_004; Scored: {lint_res.security_score}/100)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Terraform Security Linter: {type(e).__name__}: {e}")

        # Check 5: Execution Plan Risk Engine & Destructive Detection
        try:
            plan_with_destruction = (
                "Plan: 2 to add, 1 to change, 1 to destroy.\n"
                "# aws_db_instance.postgres will be destroyed\n"
                "# aws_instance.web will be created\n"
            )
            plan_res: PlanAnalysisResult = terraform_plan_engine.analyze_plan(plan_with_destruction)
            assert plan_res.to_add == 2, f"Expected 2 to add, got {plan_res.to_add}"
            assert plan_res.to_destroy == 1, f"Expected 1 to destroy, got {plan_res.to_destroy}"
            assert plan_res.destructive_changes is True
            assert any("aws_db_instance" in r for r in plan_res.destructive_reasons)
            assert plan_res.requires_human_approval is True
            assert plan_res.approval_status == "AWAITING_APPROVAL"

            print(f" [PASS] 5. Execution Plan Risk Engine: OK (Detected database destruction; flagged destructive change and required approval)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Plan Risk Engine: {type(e).__name__}: {e}")

        # Check 6: Human-in-the-Loop (HITL) Infrastructure Approval Gate
        try:
            appr_token = "token-veri-phase13-987"
            rec = terraform_plan_engine.record_approval(
                approval_token=appr_token,
                approver="lead-devops-architect",
                approved=True,
                comment="Database migration verified and approved for destruction."
            )
            assert rec["status"] == "APPROVED"
            assert rec["approver"] == "lead-devops-architect"

            fetched = terraform_plan_engine.get_approval(appr_token)
            assert fetched is not None
            assert fetched["status"] == "APPROVED"

            print(f" [PASS] 6. Human-in-the-Loop Approval Gate: OK (Registered explicit approval token: {appr_token[:14]}...)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Approval Gate: {type(e).__name__}: {e}")

        # Check 7: End-to-End Kubernetes & Terraform REST APIs
        try:
            # 1. POST /api/kubernetes/generate
            r_k8s_gen = client.post("/api/kubernetes/generate", json={
                "app_name": "payments-api",
                "container_port": 8080,
                "replicas": 3,
                "enable_hpa": True,
                "enable_ingress": True
            })
            assert r_k8s_gen.status_code == 200, f"k8s gen failed: {r_k8s_gen.text}"
            k8s_data = r_k8s_gen.json()
            assert "payments-api" in k8s_data["deployment_yaml"]
            assert k8s_data["validation"]["security_score"] >= 80

            # 2. POST /api/kubernetes/validate
            r_k8s_val = client.post("/api/kubernetes/validate", json={
                "manifest_yaml": k8s_data["all_manifests_combined"]
            })
            assert r_k8s_val.status_code == 200, f"k8s val failed: {r_k8s_val.text}"
            assert r_k8s_val.json()["is_valid"] is True

            # 3. POST /api/kubernetes/commit
            r_k8s_com = client.post("/api/kubernetes/commit", json={
                "repository_id": "default-repo",
                "branch_name": "devpilot/k8s-api-verify",
                "manifest_yaml": k8s_data["all_manifests_combined"]
            })
            assert r_k8s_com.status_code == 200, f"k8s com failed: {r_k8s_com.text}"
            assert r_k8s_com.json()["success"] is True

            # 4. POST /api/terraform/fmt
            r_tf_fmt = client.post("/api/terraform/fmt", json={
                "hcl_content": 'resource "aws_s3_bucket" "b" {\nbucket="sample"\nacl="private"\n}\n'
            })
            assert r_tf_fmt.status_code == 200, f"tf fmt failed: {r_tf_fmt.text}"
            assert '  bucket = "sample"' in r_tf_fmt.json()["formatted_content"]

            # 5. POST /api/terraform/analyse
            r_tf_ana = client.post("/api/terraform/analyse", json={
                "hcl_content": 'resource "aws_security_group" "sg" {\n  name = "sg"\n  ingress {\n    from_port = 80\n    to_port = 80\n    protocol = "tcp"\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n  tags = { Environment = "prod" }\n}\n'
            })
            assert r_tf_ana.status_code == 200, f"tf ana failed: {r_tf_ana.text}"
            assert "security_score" in r_tf_ana.json()

            # 6. POST /api/terraform/plan
            r_tf_plan = client.post("/api/terraform/plan", json={
                "plan_text": "Plan: 3 to add, 0 to change, 1 to destroy.\n# aws_db_instance.db will be destroyed"
            })
            assert r_tf_plan.status_code == 200, f"tf plan failed: {r_tf_plan.text}"
            plan_out = r_tf_plan.json()
            assert plan_out["destructive_changes"] is True
            token = plan_out["approval_token"]

            # 7. POST /api/terraform/approve
            r_tf_appr = client.post("/api/terraform/approve", json={
                "approval_token": token,
                "approved": True,
                "approver": "cloud-sec-officer"
            })
            assert r_tf_appr.status_code == 200, f"tf appr failed: {r_tf_appr.text}"
            assert r_tf_appr.json()["status"] == "APPROVED"

            print(f" [PASS] 7. End-to-End Infrastructure REST APIs: OK (/k8s/generate, /validate, /commit, /tf/fmt, /analyse, /plan, /approve)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. Infrastructure REST APIs: {type(e).__name__}: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 13 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks


if __name__ == "__main__":
    success = run_phase13_verification()
    sys.exit(0 if success else 1)
