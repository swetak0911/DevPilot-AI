"""
DevPilot AI - Build Tool and Framework Detection Engine
Discovers project architecture, language runtimes, package managers,
test runners, and linters across repository files.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import os
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class FrameworkDetectionReport:
    primary_language: str
    detected_frameworks: List[str]
    build_tool: str  # pip, poetry, npm, pnpm, yarn, maven, gradle, cargo, go
    test_runner: str  # pytest, jest, vitest, mvn test, gradle test, cargo test, go test
    linter: Optional[str]  # ruff, flake8, eslint, clippy
    has_docker: bool
    has_tests: bool
    has_linting: bool
    recommended_matrix: Dict[str, List[str]] = field(default_factory=dict)
    manifest_paths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_language": self.primary_language,
            "detected_frameworks": self.detected_frameworks,
            "build_tool": self.build_tool,
            "test_runner": self.test_runner,
            "linter": self.linter,
            "has_docker": self.has_docker,
            "has_tests": self.has_tests,
            "has_linting": self.has_linting,
            "recommended_matrix": self.recommended_matrix,
            "manifest_paths": self.manifest_paths
        }


class FrameworkDetector:
    """Scans repository files and accurately identifies project toolchains."""

    def detect(self, repo_path: str) -> FrameworkDetectionReport:
        """Analyzes directory tree and returns comprehensive detection report."""
        files = []
        try:
            for root, dirs, filenames in os.walk(repo_path):
                # prune heavy dirs
                dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", "__pycache__", "execution"]]
                for f in filenames:
                    rel_path = os.path.relpath(os.path.join(root, f), repo_path).replace("\\", "/")
                    files.append(rel_path)
        except Exception as e:
            logger.warning(f"Error walking repo path {repo_path}: {e}")

        return self.detect_from_file_list(repo_path, files)

    def detect_from_file_list(self, repo_path: str, files: List[str]) -> FrameworkDetectionReport:
        """Determines project characteristics from relative file paths."""
        frameworks: List[str] = []
        manifests: List[str] = []
        has_docker = any(f == "Dockerfile" or f.endswith("/Dockerfile") or f == "docker-compose.yml" for f in files)

        # 1. Python Detection
        py_manifests = [f for f in files if f in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "poetry.lock"] or f.endswith("/requirements.txt")]
        if py_manifests:
            manifests.extend(py_manifests)
            primary_lang = "Python"
            build_tool = "poetry" if any("poetry" in f for f in py_manifests) else "pip"
            linter = "ruff"
            test_runner = "pytest"

            # Parse dependencies if requirements.txt exists
            for req in py_manifests:
                full_p = os.path.join(repo_path, req)
                if os.path.exists(full_p):
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read().lower()
                            if "fastapi" in content:
                                frameworks.append("FastAPI")
                            if "django" in content:
                                frameworks.append("Django")
                            if "flask" in content:
                                frameworks.append("Flask")
                            if "torch" in content or "pytorch" in content:
                                frameworks.append("PyTorch")
                            if "ruff" in content:
                                linter = "ruff"
                            elif "flake8" in content:
                                linter = "flake8"
                    except Exception:
                        pass

            if not frameworks:
                frameworks.append("FastAPI")

            has_tests = any("test" in f.lower() for f in files)
            return FrameworkDetectionReport(
                primary_language=primary_lang,
                detected_frameworks=list(set(frameworks)),
                build_tool=build_tool,
                test_runner=test_runner,
                linter=linter,
                has_docker=has_docker,
                has_tests=has_tests,
                has_linting=True,
                recommended_matrix={"python-version": ["3.11", "3.12"]},
                manifest_paths=manifests
            )

        # 2. Node.js / JavaScript / TypeScript Detection
        pkg_manifests = [f for f in files if f == "package.json" or f.endswith("/package.json")]
        if pkg_manifests:
            manifests.extend(pkg_manifests)
            primary_lang = "TypeScript" if any(f.endswith(".ts") or f.endswith(".tsx") for f in files) else "JavaScript"
            build_tool = "npm"
            if "pnpm-lock.yaml" in files:
                build_tool = "pnpm"
            elif "yarn.lock" in files:
                build_tool = "yarn"

            test_runner = "npm test"
            linter = "eslint"

            for pkg in pkg_manifests:
                full_p = os.path.join(repo_path, pkg)
                if os.path.exists(full_p):
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                            data = json.load(f)
                            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                            if "react" in deps:
                                frameworks.append("React")
                            if "vite" in deps:
                                frameworks.append("Vite")
                            if "next" in deps:
                                frameworks.append("Next.js")
                            if "express" in deps:
                                frameworks.append("Express")
                            if "vitest" in deps:
                                test_runner = "vitest"
                            elif "jest" in deps:
                                test_runner = "jest"
                    except Exception:
                        pass

            return FrameworkDetectionReport(
                primary_language=primary_lang,
                detected_frameworks=list(set(frameworks)) or ["Node.js"],
                build_tool=build_tool,
                test_runner=test_runner,
                linter=linter,
                has_docker=has_docker,
                has_tests=True,
                has_linting=True,
                recommended_matrix={"node-version": ["18.x", "20.x"]},
                manifest_paths=manifests
            )

        # 3. Java / Kotlin Detection
        java_manifests = [f for f in files if f in ["pom.xml", "build.gradle", "build.gradle.kts"]]
        if java_manifests:
            manifests.extend(java_manifests)
            build_tool = "maven" if "pom.xml" in java_manifests else "gradle"
            test_runner = "mvn test" if build_tool == "maven" else "gradle test"
            return FrameworkDetectionReport(
                primary_language="Java",
                detected_frameworks=["Spring Boot"],
                build_tool=build_tool,
                test_runner=test_runner,
                linter="checkstyle",
                has_docker=has_docker,
                has_tests=True,
                has_linting=True,
                recommended_matrix={"java-version": ["17", "21"]},
                manifest_paths=manifests
            )

        # 4. Go Detection
        if "go.mod" in files:
            manifests.append("go.mod")
            return FrameworkDetectionReport(
                primary_language="Go",
                detected_frameworks=["Go Standard Library"],
                build_tool="go",
                test_runner="go test ./...",
                linter="golangci-lint",
                has_docker=has_docker,
                has_tests=True,
                has_linting=True,
                recommended_matrix={"go-version": ["1.21", "1.22"]},
                manifest_paths=manifests
            )

        # 5. Rust Detection
        if "Cargo.toml" in files:
            manifests.append("Cargo.toml")
            return FrameworkDetectionReport(
                primary_language="Rust",
                detected_frameworks=["Cargo"],
                build_tool="cargo",
                test_runner="cargo test",
                linter="cargo clippy",
                has_docker=has_docker,
                has_tests=True,
                has_linting=True,
                recommended_matrix={"rust-toolchain": ["stable"]},
                manifest_paths=manifests
            )

        # Default fallback
        return FrameworkDetectionReport(
            primary_language="Python",
            detected_frameworks=["FastAPI"],
            build_tool="pip",
            test_runner="pytest",
            linter="ruff",
            has_docker=has_docker,
            has_tests=True,
            has_linting=True,
            recommended_matrix={"python-version": ["3.11"]},
            manifest_paths=[]
        )


framework_detector = FrameworkDetector()
