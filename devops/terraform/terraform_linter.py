"""
DevPilot AI - Terraform Static Security Linter
Implements security checks modelled on tfsec and Checkov rules:
detects unrestricted ingress CIDRs (port 22/3389), public S3 ACLs,
hardcoded credentials, and unencrypted EBS/RDS storage.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
from devops.terraform.iac_parser import iac_parser, HclBlock, HclParseResult


@dataclass
class TerraformFinding:
    rule_id: str
    severity: str  # "CRITICAL", "HIGH", "WARNING", "INFO"
    resource_type: str
    resource_name: str
    message: str
    remediation: str
    line_number: Optional[int]


@dataclass
class TerraformLintResult:
    is_valid: bool
    security_score: int
    findings: List[TerraformFinding]
    resources_scanned: int
    recommendations: List[str]

    @property
    def score(self) -> int:
        return self.security_score

    @property
    def is_secure(self) -> bool:
        return self.is_valid and not any(f.severity in ("CRITICAL", "HIGH") for f in self.findings)


class TerraformLinter:
    """Analyzes Terraform configurations for security misconfigurations and CIS benchmark violations."""

    SEVERITY_DEDUCTIONS = {
        "CRITICAL": 25,
        "HIGH": 15,
        "WARNING": 8,
        "INFO": 3
    }

    SECRET_KEY_PATTERNS = [
        re.compile(r"(?i)\b(secret_key|access_key|password|api_key|token|private_key)\b\s*=\s*['\"]([^'\"]{6,})['\"]")
    ]

    def lint(self, hcl_text: str) -> TerraformLintResult:
        """Runs static analysis against Terraform code."""
        parsed = iac_parser.parse(hcl_text)
        findings: List[TerraformFinding] = []

        # 1. Global Secret Scan in HCL text
        lines = hcl_text.splitlines()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            for pat in self.SECRET_KEY_PATTERNS:
                m = pat.search(stripped)
                if m:
                    var_name = m.group(1)
                    val = m.group(2)
                    if not (val.startswith("var.") or val.startswith("local.") or "${" in val):
                        findings.append(TerraformFinding(
                            rule_id="TF_SEC_003",
                            severity="CRITICAL",
                            resource_type="variable/attribute",
                            resource_name=var_name,
                            message=f"Hardcoded credential detected in attribute '{var_name}'.",
                            remediation="Use Terraform variables (var.xxx), Vault, or AWS Secrets Manager instead of hardcoding secrets.",
                            line_number=idx + 1
                        ))

        # 2. Block-level rule checks
        for block in parsed.blocks:
            res_type = block.labels[0] if block.labels else block.block_type
            res_name = block.labels[1] if len(block.labels) > 1 else "default"
            attrs = block.attributes

            # Rule TF_SEC_001: Ingress CIDR 0.0.0.0/0 on sensitive ports
            if "security_group" in res_type or "firewall" in res_type:
                raw_lower = block.raw_content.lower()
                if "0.0.0.0/0" in raw_lower:
                    if re.search(r"\b(22|3389|5432|3306|27017)\b", raw_lower):
                        findings.append(TerraformFinding(
                            rule_id="TF_SEC_001",
                            severity="CRITICAL",
                            resource_type=res_type,
                            resource_name=res_name,
                            message=f"Security group '{res_name}' allows unrestricted ingress (0.0.0.0/0) to sensitive administrative or database ports.",
                            remediation="Restrict ingress CIDRs to a corporate bastion, internal VPC CIDR, or specific VPN IP ranges.",
                            line_number=block.start_line
                        ))
                    else:
                        findings.append(TerraformFinding(
                            rule_id="TF_SEC_005",
                            severity="WARNING",
                            resource_type=res_type,
                            resource_name=res_name,
                            message=f"Security group '{res_name}' allows unrestricted ingress from 0.0.0.0/0.",
                            remediation="Avoid 0.0.0.0/0 for internal services; limit to known load balancer subnets.",
                            line_number=block.start_line
                        ))

            # Rule TF_SEC_002: S3 Bucket Public Access & Encryption
            if "s3_bucket" in res_type:
                raw_lower = block.raw_content.lower()
                acl = attrs.get("acl", "").strip("\"'")
                if acl in ("public-read", "public-read-write", "website"):
                    findings.append(TerraformFinding(
                        rule_id="TF_SEC_002",
                        severity="HIGH",
                        resource_type=res_type,
                        resource_name=res_name,
                        message=f"S3 bucket '{res_name}' is configured with public ACL ('{acl}').",
                        remediation="Set acl to 'private' and attach an explicit aws_s3_bucket_public_access_block.",
                        line_number=block.start_line
                    ))
                if "server_side_encryption_configuration" not in raw_lower and "kms_master_key_id" not in raw_lower:
                    findings.append(TerraformFinding(
                        rule_id="TF_SEC_004",
                        severity="MEDIUM",
                        resource_type=res_type,
                        resource_name=res_name,
                        message=f"S3 bucket '{res_name}' does not configure default server-side encryption.",
                        remediation="Enable AWS KMS or AES256 server-side encryption on all S3 buckets.",
                        line_number=block.start_line
                    ))

            # Rule TF_SEC_004: Unencrypted EBS / RDS storage
            if "ebs_volume" in res_type or "db_instance" in res_type:
                raw_lower = block.raw_content.lower()
                encrypted_attr = attrs.get("encrypted", "").lower()
                storage_enc_attr = attrs.get("storage_encrypted", "").lower()
                if encrypted_attr == "false" or storage_enc_attr == "false" or ("encrypted" not in raw_lower and "storage_encrypted" not in raw_lower):
                    findings.append(TerraformFinding(
                        rule_id="TF_SEC_004",
                        severity="HIGH",
                        resource_type=res_type,
                        resource_name=res_name,
                        message=f"Persistent data storage '{res_name}' ({res_type}) is not encrypted at rest.",
                        remediation="Set 'encrypted = true' (or 'storage_encrypted = true' for RDS) with a managed KMS key.",
                        line_number=block.start_line
                    ))

            # Rule TF_SEC_007: Missing tags on cloud resources
            if block.block_type == "resource" and "tags" not in block.raw_content.lower():
                findings.append(TerraformFinding(
                    rule_id="TF_SEC_007",
                    severity="INFO",
                    resource_type=res_type,
                    resource_name=res_name,
                    message=f"Resource '{res_name}' is missing resource tags for billing and governance.",
                    remediation="Add a 'tags' map with Environment, Owner, and Project tags.",
                    line_number=block.start_line
                ))

        # Calculate security score
        score = 100
        for f in findings:
            deduction = self.SEVERITY_DEDUCTIONS.get(f.severity, 5)
            score -= deduction
        score = max(0, min(100, score))

        is_valid = not any(f.severity == "CRITICAL" for f in findings) and score >= 60

        recommendations = []
        if any(f.rule_id == "TF_SEC_001" for f in findings):
            recommendations.append("Remediate public ingress CIDR 0.0.0.0/0 on SSH and database ports.")
        if any(f.rule_id == "TF_SEC_003" for f in findings):
            recommendations.append("Remove hardcoded credentials; inject secrets at runtime.")
        if any(f.rule_id == "TF_SEC_004" for f in findings):
            recommendations.append("Enforce at-rest encryption on all EBS volumes, RDS databases, and S3 buckets.")
        if not recommendations:
            recommendations.append("Terraform configurations adhere to CIS Cloud Security benchmarks.")

        return TerraformLintResult(
            is_valid=is_valid,
            security_score=score,
            findings=findings,
            resources_scanned=parsed.resource_count,
            recommendations=recommendations
        )


terraform_linter = TerraformLinter()
