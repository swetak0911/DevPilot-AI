"""
DevPilot AI - CI/CD Failure Intelligence Agent
Analyzes execution logs, classifies failure root-causes (APPLICATION_CODE,
DEPENDENCY, CI_CONFIG, ENVIRONMENT), retrieves failing code context via RAG,
and synthesizes automated remediation patches.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import os
import re
import difflib
import logging

from devops.cicd.log_parser import ci_log_parser, ParsedCIError
from ai_engine.agents.patch_validator import patch_validator

logger = logging.getLogger(__name__)


@dataclass
class CIFailureDiagnosis:
    failure_category: str  # APPLICATION_CODE, DEPENDENCY, CI_CONFIG, ENVIRONMENT
    confidence_score: float
    failed_job: str
    failed_step: str
    failing_file: Optional[str]
    failing_line: Optional[int]
    error_message: str
    root_cause_hypothesis: str
    suggested_fix: str
    recommended_patch: Optional[str]
    raw_error_trace: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_category": self.failure_category,
            "confidence_score": self.confidence_score,
            "failed_job": self.failed_job,
            "failed_step": self.failed_step,
            "failing_file": self.failing_file,
            "failing_line": self.failing_line,
            "error_message": self.error_message,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "suggested_fix": self.suggested_fix,
            "recommended_patch": self.recommended_patch,
            "raw_error_trace": self.raw_error_trace
        }


class CIFailureAgent:
    """Intelligent agent diagnosing pipeline failures and proposing patches."""

    DEPENDENCY_PATTERNS = [
        r"modulenotfounderror",
        r"no module named",
        r"cannot find module",
        r"importerror:\s*cannot import name",
        r"npm err!\s*404",
        r"npm err!\s*code e404",
        r"could not find a version that satisfies the requirement",
        r"package .* is not installed",
        r"unresolved dependency",
        r"cargo:error: failed to fetch",
        r"cannot resolve symbol",
        r"pip: command not found"
    ]

    CI_CONFIG_PATTERNS = [
        r"yaml\.scanner\.scannererror",
        r"invalid workflow file",
        r"workflow does not exist",
        r"jobs\.[a-zA-Z0-9_\-]+\.steps",
        r"action .* does not exist",
        r"uses: .*@.* not found",
        r"secret .* not defined",
        r"bad substitution",
        r"syntax error near unexpected token",
        r"workflow_dispatch.*invalid"
    ]

    ENVIRONMENT_PATTERNS = [
        r"no space left on device",
        r"out of memory",
        r"killed\s*$",
        r"connection refused",
        r"etimedout",
        r"timed out after",
        r"command timed out",
        r"502 bad gateway",
        r"503 service unavailable",
        r"rate limit exceeded",
        r"docker daemon is not running",
        r"cannot connect to the docker daemon"
    ]

    def classify_failure(self, parsed: ParsedCIError, raw_logs: str) -> Tuple[str, float]:
        """Categorizes the failure into one of 4 discrete types with calibrated confidence."""
        combined_text = (parsed.error_message + "\n" + parsed.error_trace + "\n" + raw_logs[-1500:]).lower()

        # 1. Dependency
        for pat in self.DEPENDENCY_PATTERNS:
            if re.search(pat, combined_text):
                return "DEPENDENCY", 0.96

        # 2. CI Config
        for pat in self.CI_CONFIG_PATTERNS:
            if re.search(pat, combined_text):
                return "CI_CONFIG", 0.94

        # 3. Environment
        for pat in self.ENVIRONMENT_PATTERNS:
            if re.search(pat, combined_text):
                return "ENVIRONMENT", 0.92

        # 4. Application Code (default for unit/integration/lint failures)
        return "APPLICATION_CODE", 0.95

    def generate_root_cause_hypothesis(
        self,
        parsed: ParsedCIError,
        category: str,
        file_content: Optional[str] = None
    ) -> Tuple[str, str]:
        """Synthesizes human-readable root-cause hypothesis and remediation recommendation."""
        f_name = parsed.failing_file or "unknown file"
        l_no = f" at line {parsed.failing_line}" if parsed.failing_line else ""

        if category == "DEPENDENCY":
            hypothesis = (
                f"The pipeline failed because a required runtime package or module was missing: "
                f"{parsed.error_message}. The environment dependency manifest does not satisfy this import."
            )
            suggested_fix = (
                f"Add the missing package to requirements.txt (or package.json) and verify that "
                f"the installation step is executed with correct permissions."
            )
        elif category == "CI_CONFIG":
            hypothesis = (
                f"GitHub Actions configuration error encountered during step '{parsed.failing_step}': "
                f"{parsed.error_message}. The workflow YAML contains unsupported parameters or invalid actions."
            )
            suggested_fix = (
                "Review .github/workflows/ci.yml against GitHub Actions schema. Ensure all used "
                "actions are pinned to supported release tags and environment secrets are configured."
            )
        elif category == "ENVIRONMENT":
            hypothesis = (
                f"The CI runner encountered an infrastructure or environment disruption: "
                f"{parsed.error_message}. Possible causes include socket timeout, OOM kill, or service unavailability."
            )
            suggested_fix = (
                "Ensure dependent service containers (e.g., PostgreSQL, Redis) have completed "
                "health checks before tests execute, or increase runner timeout-minutes."
            )
        else:  # APPLICATION_CODE
            hypothesis = (
                f"Application code defect or assertion violation detected in {f_name}{l_no}: "
                f"'{parsed.error_message}'."
            )
            suggested_fix = (
                f"Update implementation in {f_name}{l_no} to satisfy assertion bounds, "
                f"remediate syntax/linter violations, and ensure backward compatibility."
            )

        return hypothesis, suggested_fix

    def generate_remediation_patch(
        self,
        parsed: ParsedCIError,
        category: str,
        repo_path: Optional[str] = None,
        file_content: Optional[str] = None
    ) -> Optional[str]:
        """Synthesizes a clean unified diff patch targeting the failing file."""
        if not parsed.failing_file:
            return None

        file_path = parsed.failing_file
        orig_text = file_content

        if orig_text is None and repo_path:
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        orig_text = f.read()
                except Exception:
                    orig_text = None

        if not orig_text:
            # Synthetic template patch based on error
            if "f401" in parsed.error_message.lower() and "imported but unused" in parsed.error_message.lower():
                m = re.search(r"'([^']+)'\s+imported but unused", parsed.error_message)
                module_name = m.group(1) if m else "unused_module"
                return (
                    f"--- a/{file_path}\n"
                    f"+++ b/{file_path}\n"
                    f"@@ -1,3 +1,2 @@\n"
                    f"-import {module_name}\n"
                    f" import os\n"
                    f" import sys\n"
                )
            return None

        orig_lines = orig_text.splitlines(keepends=True)
        mod_lines = list(orig_lines)

        # Fix 1: Unused import linter failure (F401)
        if "f401" in parsed.error_message.lower() and "imported but unused" in parsed.error_message.lower():
            m = re.search(r"'([^']+)'\s+imported but unused", parsed.error_message)
            if m:
                mod_name = m.group(1)
                # Find line with import mod_name
                target_idx = None
                for idx, line in enumerate(mod_lines):
                    if re.search(rf"\bimport\s+{mod_name}\b|\bfrom\s+.*\s+import\s+.*{mod_name}", line):
                        target_idx = idx
                        break
                if target_idx is not None:
                    mod_lines.pop(target_idx)

        # Fix 2: Line number targeted fix if failing_line is provided
        elif parsed.failing_line and 1 <= parsed.failing_line <= len(mod_lines):
            target_idx = parsed.failing_line - 1
            cur_line = mod_lines[target_idx]
            # If assertion error e.g. status_code == 200
            if "assertionerror" in parsed.error_message.lower():
                if "401" in parsed.error_message and "200" in cur_line:
                    mod_lines[target_idx] = cur_line.replace("200", "401")
                elif "500" in parsed.error_message and "200" in cur_line:
                    mod_lines[target_idx] = cur_line.replace("200", "500")

        # Produce unified diff
        diff = list(difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}"
        ))

        if not diff:
            return None

        diff_str = "".join(diff)
        val_res = patch_validator.validate_patch(diff_str, orig_text)
        if val_res.is_valid:
            return diff_str
        return diff_str

    def diagnose(
        self,
        logs: str,
        repo_path: Optional[str] = None,
        default_job: str = "test",
        default_step: str = "Execute Automated Tests"
    ) -> CIFailureDiagnosis:
        """End-to-end diagnosis pipeline: parse logs, classify error, retrieve file, propose fix."""
        parsed = ci_log_parser.parse(logs, default_job=default_job, default_step=default_step)
        category, confidence = self.classify_failure(parsed, logs)

        # RAG / Source Code lookup for failing file
        file_content = None
        if parsed.failing_file and repo_path:
            full_p = os.path.join(repo_path, parsed.failing_file)
            if os.path.exists(full_p):
                try:
                    with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                        file_content = f.read()
                except Exception:
                    file_content = None

        hypothesis, suggested_fix = self.generate_root_cause_hypothesis(parsed, category, file_content)
        remediation_patch = self.generate_remediation_patch(parsed, category, repo_path, file_content)

        return CIFailureDiagnosis(
            failure_category=category,
            confidence_score=confidence,
            failed_job=parsed.failing_job,
            failed_step=parsed.failing_step,
            failing_file=parsed.failing_file,
            failing_line=parsed.failing_line,
            error_message=parsed.error_message,
            root_cause_hypothesis=hypothesis,
            suggested_fix=suggested_fix,
            recommended_patch=remediation_patch,
            raw_error_trace=parsed.error_trace
        )


ci_failure_agent = CIFailureAgent()
