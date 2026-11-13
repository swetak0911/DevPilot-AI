"""
DevPilot AI - Dockerfile Security & Best-Practice Linter
Implements static rule validation modelled on Hadolint and Docker CIS Benchmarks.
Identifies root execution vulnerabilities, unpinned image tags, package cache pollution,
hardcoded secrets, and missing healthcheck probes.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re


@dataclass
class DockerLintIssue:
    code: str
    severity: str  # "CRITICAL", "HIGH", "WARNING", "INFO"
    line_number: Optional[int]
    message: str
    suggestion: str


@dataclass
class DockerLintResult:
    is_valid: bool
    security_score: int
    issues: List[DockerLintIssue]
    layer_count: int
    stages_detected: List[str]

    @property
    def score(self) -> int:
        return self.security_score

    @property
    def is_hardened(self) -> bool:
        return self.is_valid and not any(i.severity in ("CRITICAL", "HIGH") for i in self.issues)


class DockerLinter:
    """Performs comprehensive static analysis and security scanning on Dockerfiles."""

    SECRET_ENV_PATTERNS = [
        re.compile(r"(?i)\b[A-Z0-9_]*(?:SECRET|PASSWORD|TOKEN|API_KEY|PRIVATE_KEY|AUTH_KEY|CREDENTIALS?)[A-Z0-9_]*\s*="),
        re.compile(r"(?i)(password|secret|token|api_key|private_key|auth_key|credentials?)\s*=?\s*['\"]?[a-zA-Z0-9_\-\.]{8,}['\"]?"),
        re.compile(r"(?i)\b(AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|DATABASE_PASSWORD|SECRET_API_KEY)\b")
    ]

    SEVERITY_WEIGHTS = {
        "CRITICAL": 25,
        "HIGH": 15,
        "WARNING": 8,
        "INFO": 3
    }

    def lint(self, dockerfile_content: str) -> DockerLintResult:
        """Lints Dockerfile content against CIS security rules and Hadolint conventions."""
        lines = dockerfile_content.splitlines()
        issues: List[DockerLintIssue] = []

        stages: List[str] = []
        user_instructions: List[tuple[int, str]] = []
        from_instructions: List[tuple[int, str]] = []
        has_healthcheck = False
        consecutive_runs = 0
        copy_all_line = None
        dep_install_line = None
        layer_count = 0

        for idx, line in enumerate(lines):
            line_no = idx + 1
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                consecutive_runs = 0
                continue

            # Count layers
            first_word = stripped.split()[0].upper()
            if first_word in ("FROM", "RUN", "COPY", "ADD", "ENV", "EXPOSE", "USER", "WORKDIR", "ENTRYPOINT", "CMD"):
                layer_count += 1

            # 1. Track FROM instructions & stages
            if stripped.upper().startswith("FROM "):
                consecutive_runs = 0
                from_instructions.append((line_no, stripped))
                parts = stripped.split()
                if len(parts) >= 2:
                    image_tag = parts[1]
                    # Check DL3006: Tag pinning
                    if ":" not in image_tag or image_tag.endswith(":latest"):
                        issues.append(DockerLintIssue(
                            code="DL3006",
                            severity="WARNING",
                            line_number=line_no,
                            message=f"Base image '{image_tag}' uses ':latest' or unpinned tag.",
                            suggestion="Pin the image version explicitly to a major/minor or digest (e.g., 'python:3.11-slim')."
                        ))
                if " AS " in stripped.upper():
                    stage_name = stripped.upper().split(" AS ")[1].strip().split()[0]
                    stages.append(stage_name.lower())
                else:
                    stages.append(f"stage_{len(stages)+1}")

            # 2. Track USER instructions
            elif stripped.upper().startswith("USER "):
                consecutive_runs = 0
                user_name = stripped.split()[1]
                user_instructions.append((line_no, user_name))

            # 3. Track HEALTHCHECK
            elif stripped.upper().startswith("HEALTHCHECK "):
                consecutive_runs = 0
                has_healthcheck = True

            # 4. Check RUN instructions
            elif stripped.upper().startswith("RUN "):
                consecutive_runs += 1
                if consecutive_runs >= 2:
                    issues.append(DockerLintIssue(
                        code="DL3059",
                        severity="INFO",
                        line_number=line_no,
                        message="Multiple consecutive RUN instructions detected.",
                        suggestion="Combine consecutive RUN instructions using '&&' and line breaks to minimize intermediate layers."
                    ))

                # DL3008 & DL3015: apt-get best practices
                if "apt-get install" in stripped:
                    if "--no-install-recommends" not in stripped:
                        issues.append(DockerLintIssue(
                            code="DL3015",
                            severity="INFO",
                            line_number=line_no,
                            message="apt-get install executed without '--no-install-recommends'.",
                            suggestion="Add '--no-install-recommends' to avoid installing unnecessary default packages."
                        ))
                    if "rm -rf /var/lib/apt/lists/*" not in dockerfile_content:
                        issues.append(DockerLintIssue(
                            code="DL3008",
                            severity="WARNING",
                            line_number=line_no,
                            message="Package cache not cleaned up after apt-get install.",
                            suggestion="Append '&& rm -rf /var/lib/apt/lists/*' in the same RUN layer to reduce image footprint."
                        ))

                # DL3042: pip install --no-cache-dir
                if "pip install" in stripped and "--no-cache-dir" not in stripped:
                    issues.append(DockerLintIssue(
                        code="DL3042",
                        severity="WARNING",
                        line_number=line_no,
                        message="pip install executed without '--no-cache-dir'.",
                        suggestion="Specify '--no-cache-dir' with pip to prevent caching downloaded wheel tarballs."
                    ))

                # Track dep install line for caching check
                if any(k in stripped for k in ("pip install", "npm install", "npm ci", "go mod download", "mvn ", "cargo build")):
                    if dep_install_line is None:
                        dep_install_line = line_no

            # 5. Check COPY instructions for caching order
            elif stripped.upper().startswith("COPY "):
                consecutive_runs = 0
                # Check if copying current dir before dependency install
                args = stripped.split()
                if len(args) >= 3 and args[1] == "." and dep_install_line is None:
                    copy_all_line = line_no

            # 6. Check ENV for secrets (SEC101)
            elif stripped.upper().startswith("ENV "):
                consecutive_runs = 0
                for pat in self.SECRET_ENV_PATTERNS:
                    if pat.search(stripped):
                        issues.append(DockerLintIssue(
                            code="SEC101",
                            severity="CRITICAL",
                            line_number=line_no,
                            message="Potential hardcoded secret or sensitive credential found in ENV directive.",
                            suggestion="Do not bake secrets into container images. Inject credentials at runtime via Docker secrets or environment variables."
                        ))
                        break
            else:
                consecutive_runs = 0

        # DL3002: Non-root user check
        if not user_instructions:
            issues.append(DockerLintIssue(
                code="DL3002",
                severity="HIGH",
                line_number=len(lines),
                message="No USER instruction declared; container will execute as root.",
                suggestion="Create an unprivileged user (e.g. 'appuser' with UID 10001) and add 'USER appuser' before CMD/ENTRYPOINT."
            ))
        else:
            last_line, last_user = user_instructions[-1]
            if last_user.lower() in ("root", "0"):
                issues.append(DockerLintIssue(
                    code="DL3002",
                    severity="HIGH",
                    line_number=last_line,
                    message="Final USER instruction explicitly sets user to 'root'.",
                    suggestion="Switch to a non-privileged user before the final container entrypoint."
                ))

        # SEC102: Missing HEALTHCHECK
        if not has_healthcheck:
            issues.append(DockerLintIssue(
                code="SEC102",
                severity="WARNING",
                line_number=len(lines),
                message="Missing HEALTHCHECK instruction.",
                suggestion="Add a HEALTHCHECK instruction so orchestrators (Kubernetes, Docker Swarm) can monitor container liveliness."
            ))

        # PERF101: Caching violation
        if copy_all_line is not None and dep_install_line is not None and copy_all_line < dep_install_line:
            issues.append(DockerLintIssue(
                code="PERF101",
                severity="WARNING",
                line_number=copy_all_line,
                message="Entire workspace ('COPY . .') copied prior to installing dependencies.",
                suggestion="Copy manifest files first (e.g. requirements.txt or package.json), install dependencies, then copy remaining application source."
            ))

        # PERF102: Multi-stage check
        if len(from_instructions) < 2:
            issues.append(DockerLintIssue(
                code="PERF102",
                severity="INFO",
                line_number=1,
                message="Single-stage build detected.",
                suggestion="Consider converting to a multi-stage Dockerfile to separate the build toolchain from the runtime image."
            ))

        # Calculate security score (0 - 100)
        score = 100
        for issue in issues:
            deduction = self.SEVERITY_WEIGHTS.get(issue.severity, 5)
            score -= deduction
        score = max(0, min(100, score))

        is_valid = not any(i.severity == "CRITICAL" for i in issues) and score >= 60

        return DockerLintResult(
            is_valid=is_valid,
            security_score=score,
            issues=issues,
            layer_count=layer_count,
            stages_detected=stages
        )


docker_linter = DockerLinter()
