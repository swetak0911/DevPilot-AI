"""
DevPilot AI - Static Secret Scanner & Security Audit Guard
Scans source code, configuration files, and unified diffs for credential leaks,
hardcoded secrets, private keys, and path traversal vulnerabilities.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class SecretFinding:
    rule_id: str
    description: str
    severity: str  # "HIGH", "CRITICAL", "MEDIUM"
    line_number: int
    matched_snippet: str
    file_path: Optional[str] = None


@dataclass
class SecurityAuditReport:
    total_files_scanned: int
    total_findings: int
    findings: List[SecretFinding]
    is_clean: bool
    summary: str


class SecretScanner:
    """Detects credentials, API keys, private keys, and dangerous patterns."""

    SECRET_PATTERNS = [
        (
            "SEC_AWS_KEY",
            "AWS Access Key ID Detected",
            "CRITICAL",
            re.compile(r"\b(AKIA[0-9A-Z]{16})\b")
        ),
        (
            "SEC_PRIVATE_KEY",
            "Unencrypted Private Key Block Detected",
            "CRITICAL",
            re.compile(r"-----BEGIN\s+(?:RSA|EC|DSA|OPENSSH|PGP)?\s*PRIVATE KEY-----")
        ),
        (
            "SEC_GITHUB_PAT",
            "GitHub Personal Access Token Detected",
            "CRITICAL",
            re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b")
        ),
        (
            "SEC_SLACK_TOKEN",
            "Slack Bot or User Token Detected",
            "HIGH",
            re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b")
        ),
        (
            "SEC_GENERIC_KEY",
            "Hardcoded API Key or Secret Password Assignment",
            "HIGH",
            re.compile(r"""(?i)(?:api_key|secret_key|auth_token|client_secret|password)\s*[:=]\s*["']([A-Za-z0-9_\-\.]{12,})["']""")
        ),
        (
            "SEC_DB_URI_PASSWORD",
            "Database Connection URI with Embedded Plaintext Password",
            "HIGH",
            re.compile(r"""(?i)(?:postgres|postgresql|mysql|mongodb)://[^:]+:([^@]+)@""")
        )
    ]

    def scan_content(self, content: str, file_path: Optional[str] = None) -> List[SecretFinding]:
        """Scans raw file content line-by-line against credential patterns."""
        findings: List[SecretFinding] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            # Skip comments or documentation examples if explicit
            stripped = line.strip()
            if stripped.startswith("#") and "example" in stripped.lower():
                continue

            for rule_id, desc, severity, pattern in self.SECRET_PATTERNS:
                match = pattern.search(line)
                if match:
                    # Redact matched secret
                    secret_val = match.group(0)
                    redacted = secret_val[:4] + "*" * min(8, len(secret_val) - 4)
                    findings.append(SecretFinding(
                        rule_id=rule_id,
                        description=desc,
                        severity=severity,
                        line_number=idx,
                        matched_snippet=line.replace(secret_val, redacted).strip(),
                        file_path=file_path
                    ))

        return findings

    def check_path_traversal(self, target_path: str, base_dir: str) -> bool:
        """
        Validates that target_path strictly resolves inside base_dir.
        Returns True if safe, False if path traversal attack detected.
        """
        try:
            norm_base = os.path.abspath(base_dir)
            norm_target = os.path.abspath(os.path.join(base_dir, target_path))
            return os.path.commonpath([norm_base, norm_target]) == norm_base
        except Exception:
            return False

    def scan_repository(self, repo_dir: str, max_files: int = 200) -> SecurityAuditReport:
        """Audits all source and configuration files in a repository directory."""
        all_findings: List[SecretFinding] = []
        files_count = 0

        exclude_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
        target_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yml", ".yaml", ".env", ".tf", ".hcl", ".sh"}

        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in target_exts or file.startswith(".env"):
                    files_count += 1
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, repo_dir)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        f_findings = self.scan_content(content, file_path=rel_path)
                        all_findings.extend(f_findings)
                    except Exception as e:
                        logger.warning(f"Could not read {rel_path} for secret scan: {e}")

                if files_count >= max_files:
                    break
            if files_count >= max_files:
                break

        is_clean = len(all_findings) == 0
        summary = (
            f"Security scan complete: {files_count} files scanned, {len(all_findings)} potential secret leaks flagged."
        )

        return SecurityAuditReport(
            total_files_scanned=files_count,
            total_findings=len(all_findings),
            findings=all_findings,
            is_clean=is_clean,
            summary=summary
        )


secret_scanner = SecretScanner()
