"""
DevPilot AI - GitHub Actions Pipeline Generator
Synthesizes optimized, production-grade GitHub Actions workflows based on detected
frameworks, package managers, matrix targets, service containers, and Docker definitions.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from devops.cicd.framework_detector import FrameworkDetectionReport


@dataclass
class PipelineGenerationResult:
    yaml_content: str
    workflow_name: str
    jobs: List[str]
    matrix_enabled: bool
    has_docker_job: bool
    has_services: bool
    suggested_path: str = ".github/workflows/ci.yml"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "yaml_content": self.yaml_content,
            "workflow_name": self.workflow_name,
            "jobs": self.jobs,
            "matrix_enabled": self.matrix_enabled,
            "has_docker_job": self.has_docker_job,
            "has_services": self.has_services,
            "suggested_path": self.suggested_path
        }


class PipelineGenerator:
    """Generates hardened, multi-job GitHub Actions workflows."""

    def generate(
        self,
        report: FrameworkDetectionReport,
        workflow_name: str = "DevPilot Continuous Integration",
        branches: Optional[List[str]] = None,
        include_linting: bool = True,
        include_tests: bool = True,
        include_matrix: bool = False,
        include_docker: bool = False,
        include_services: Optional[List[str]] = None,
        environment_vars: Optional[Dict[str, str]] = None
    ) -> PipelineGenerationResult:
        """Constructs a modular workflow conforming to GitHub Actions specification."""
        branches = branches or ["main", "develop"]
        services = include_services or []
        jobs_list: List[str] = []

        lines: List[str] = []
        # Header
        lines.append(f'name: "{workflow_name}"')
        lines.append("")
        lines.append("on:")
        lines.append("  push:")
        branch_str = ", ".join(f'"{b}"' for b in branches)
        lines.append(f"    branches: [{branch_str}]")
        lines.append("  pull_request:")
        lines.append(f"    branches: [{branch_str}]")
        lines.append("  workflow_dispatch:")
        lines.append("")
        lines.append("permissions:")
        lines.append("  contents: read")
        lines.append("  checks: write")
        lines.append("  pull-requests: write")
        lines.append("")
        lines.append("jobs:")

        lang = report.primary_language.lower()

        # Job 1: Linting Job
        if include_linting:
            jobs_list.append("lint")
            lines.append("  lint:")
            lines.append('    name: "Code Quality & Linting"')
            lines.append("    runs-on: ubuntu-latest")
            lines.append("    steps:")
            lines.append("      - name: Checkout Code")
            lines.append("        uses: actions/checkout@v4")
            lines.append("")
            self._append_runtime_setup(lines, report, matrix_var=None)
            self._append_lint_steps(lines, report)
            lines.append("")

        # Job 2: Test Job
        if include_tests:
            jobs_list.append("test")
            lines.append("  test:")
            lines.append('    name: "Automated Test Suite"')
            lines.append("    runs-on: ubuntu-latest")
            if include_linting:
                lines.append("    needs: [lint]")

            # Matrix Strategy
            if include_matrix and report.recommended_matrix:
                lines.append("    strategy:")
                lines.append("      fail-fast: false")
                lines.append("      matrix:")
                for var_name, values in report.recommended_matrix.items():
                    val_str = ", ".join(f'"{v}"' for v in values)
                    lines.append(f"        {var_name}: [{val_str}]")

            # Service Containers
            if services:
                lines.append("    services:")
                if "postgres" in services:
                    lines.append("      postgres:")
                    lines.append("        image: postgres:15-alpine")
                    lines.append("        env:")
                    lines.append("          POSTGRES_DB: devpilot_test")
                    lines.append("          POSTGRES_USER: devpilot")
                    lines.append("          POSTGRES_PASSWORD: devpilot_secret")
                    lines.append("        ports:")
                    lines.append("          - 5432:5432")
                    lines.append("        options: >-")
                    lines.append("          --health-cmd pg_isready")
                    lines.append("          --health-interval 10s")
                    lines.append("          --health-timeout 5s")
                    lines.append("          --health-retries 5")
                if "redis" in services:
                    lines.append("      redis:")
                    lines.append("        image: redis:7-alpine")
                    lines.append("        ports:")
                    lines.append("          - 6379:6379")
                    lines.append("        options: >-")
                    lines.append("          --health-cmd \"redis-cli ping\"")
                    lines.append("          --health-interval 10s")
                    lines.append("          --health-timeout 5s")
                    lines.append("          --health-retries 5")

            # Environment variables
            if environment_vars or services:
                lines.append("    env:")
                if "postgres" in services:
                    lines.append("      DATABASE_URL: postgresql://devpilot:devpilot_secret@localhost:5432/devpilot_test")
                if "redis" in services:
                    lines.append("      REDIS_URL: redis://localhost:6379/0")
                if environment_vars:
                    for k, v in environment_vars.items():
                        lines.append(f'      {k}: "{v}"')

            lines.append("    steps:")
            lines.append("      - name: Checkout Code")
            lines.append("        uses: actions/checkout@v4")
            lines.append("")
            matrix_key = list(report.recommended_matrix.keys())[0] if (include_matrix and report.recommended_matrix) else None
            self._append_runtime_setup(lines, report, matrix_var=matrix_key)
            self._append_test_steps(lines, report)

            # Upload Artifact step
            lines.append("      - name: Archive Test Results")
            lines.append("        if: always()")
            lines.append("        uses: actions/upload-artifact@v4")
            lines.append("        with:")
            lines.append("          name: test-results")
            lines.append("          path: test-results/")
            lines.append("          retention-days: 14")
            lines.append("")

        # Job 3: Docker Build Job
        if include_docker:
            jobs_list.append("docker-build")
            lines.append("  docker-build:")
            lines.append('    name: "Container Build & Validation"')
            lines.append("    runs-on: ubuntu-latest")
            needs = [j for j in ["lint", "test"] if j in jobs_list]
            if needs:
                needs_str = ", ".join(needs)
                lines.append(f"    needs: [{needs_str}]")
            lines.append("    steps:")
            lines.append("      - name: Checkout Code")
            lines.append("        uses: actions/checkout@v4")
            lines.append("")
            lines.append("      - name: Set up Docker Buildx")
            lines.append("        uses: docker/setup-buildx-action@v3")
            lines.append("")
            lines.append("      - name: Build Container Image")
            lines.append("        uses: docker/build-push-action@v5")
            lines.append("        with:")
            lines.append("          context: .")
            lines.append("          push: false")
            lines.append("          tags: devpilot-app:${{ github.sha }}")
            lines.append("")

        yaml_content = "\n".join(lines).strip() + "\n"

        return PipelineGenerationResult(
            yaml_content=yaml_content,
            workflow_name=workflow_name,
            jobs=jobs_list,
            matrix_enabled=include_matrix and bool(report.recommended_matrix),
            has_docker_job=include_docker,
            has_services=bool(services)
        )

    def _append_runtime_setup(self, lines: List[str], report: FrameworkDetectionReport, matrix_var: Optional[str] = None):
        """Generates language runtime setup with dependency caching."""
        lang = report.primary_language.lower()
        if "python" in lang:
            version_val = f"${{{{ matrix.{matrix_var} }}}}" if matrix_var else "3.11"
            lines.append("      - name: Set up Python Environment")
            lines.append("        uses: actions/setup-python@v5")
            lines.append("        with:")
            lines.append(f'          python-version: "{version_val}"')
            lines.append('          cache: "pip"')
            lines.append("")
            lines.append("      - name: Install Python Dependencies")
            lines.append("        run: |")
            lines.append("          python -m pip install --upgrade pip")
            if any("requirements.txt" in m for m in report.manifest_paths):
                req = [m for m in report.manifest_paths if "requirements.txt" in m][0]
                lines.append(f"          pip install -r {req}")
            else:
                lines.append("          pip install pytest ruff")
        elif "typescript" in lang or "javascript" in lang:
            version_val = f"${{{{ matrix.{matrix_var} }}}}" if matrix_var else "20.x"
            lines.append("      - name: Set up Node.js")
            lines.append("        uses: actions/setup-node@v4")
            lines.append("        with:")
            lines.append(f'          node-version: "{version_val}"')
            lines.append(f'          cache: "{report.build_tool}"')
            lines.append("")
            lines.append(f"      - name: Install Dependencies ({report.build_tool})")
            lines.append("        run: |")
            if report.build_tool == "pnpm":
                lines.append("          npm install -g pnpm")
                lines.append("          pnpm install --frozen-lockfile")
            elif report.build_tool == "yarn":
                lines.append("          yarn install --frozen-lockfile")
            else:
                lines.append("          npm ci || npm install")
        elif "java" in lang:
            version_val = f"${{{{ matrix.{matrix_var} }}}}" if matrix_var else "17"
            lines.append("      - name: Set up JDK")
            lines.append("        uses: actions/setup-java@v4")
            lines.append("        with:")
            lines.append(f'          java-version: "{version_val}"')
            lines.append("          distribution: 'temurin'")
            lines.append(f'          cache: "{report.build_tool}"')
        elif "go" in lang:
            version_val = f"${{{{ matrix.{matrix_var} }}}}" if matrix_var else "1.21"
            lines.append("      - name: Set up Go")
            lines.append("        uses: actions/setup-go@v5")
            lines.append("        with:")
            lines.append(f'          go-version: "{version_val}"')
            lines.append("          cache: true")
        elif "rust" in lang:
            lines.append("      - name: Set up Rust Toolchain")
            lines.append("        uses: actions-rust-lang/setup-rust-toolchain@v1")
        lines.append("")

    def _append_lint_steps(self, lines: List[str], report: FrameworkDetectionReport):
        """Generates framework linter execution step."""
        linter = report.linter or "ruff"
        lines.append("      - name: Run Code Linter")
        lines.append("        run: |")
        if linter == "ruff":
            lines.append("          ruff check .")
        elif linter == "flake8":
            lines.append("          flake8 . --count --max-line-length=120 --statistics")
        elif linter == "eslint":
            lines.append("          npm run lint || npx eslint .")
        elif linter == "golangci-lint":
            lines.append("          golangci-lint run ./...")
        elif linter == "cargo clippy":
            lines.append("          cargo clippy -- -D warnings")
        elif linter == "checkstyle":
            lines.append("          mvn checkstyle:check || true")
        else:
            lines.append(f"          {linter} .")

    def _append_test_steps(self, lines: List[str], report: FrameworkDetectionReport):
        """Generates framework test execution step with report output."""
        runner = report.test_runner or "pytest"
        lines.append("      - name: Execute Automated Tests")
        lines.append("        run: |")
        lines.append("          mkdir -p test-results")
        if "pytest" in runner:
            lines.append("          pytest --junitxml=test-results/junit.xml || true")
        elif "jest" in runner or "npm test" in runner or "vitest" in runner:
            lines.append("          npm test -- --reporter=junit --outputFile=test-results/junit.xml || npm test || true")
        elif "mvn" in runner:
            lines.append("          mvn test")
            lines.append("          cp target/surefire-reports/*.xml test-results/ || true")
        elif "gradle" in runner:
            lines.append("          gradle test")
            lines.append("          cp build/test-results/test/*.xml test-results/ || true")
        elif "go test" in runner:
            lines.append("          go test -v ./... > test-results/output.txt || true")
        elif "cargo test" in runner:
            lines.append("          cargo test")
        else:
            lines.append(f"          {runner}")
        lines.append("")


pipeline_generator = PipelineGenerator()
