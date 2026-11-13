"""
Dependency Analyzer Service
Inspects project manifests to determine programming languages, frameworks,
package managers, direct dependencies, and container configurations.
"""
import os
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DependencyAnalysisResult:
    primary_language: str
    detected_languages: List[str]
    detected_frameworks: List[str]
    package_managers: List[str]
    direct_dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    has_dockerfile: bool = False
    has_docker_compose: bool = False
    has_ci_workflows: bool = False


class DependencyAnalyzer:
    """Analyzes repository root and subdirectories for dependencies and frameworks."""

    FRAMEWORK_RULES = {
        # Python
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "torch": "PyTorch",
        "tensorflow": "TensorFlow",
        "transformers": "Hugging Face Transformers",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "celery": "Celery",
        "sqlalchemy": "SQLAlchemy",
        "pydantic": "Pydantic",

        # JavaScript / TypeScript
        "react": "React",
        "vue": "Vue.js",
        "@angular/core": "Angular",
        "next": "Next.js",
        "express": "Express",
        "tailwindcss": "Tailwind CSS",
        "vite": "Vite",

        # Java
        "spring-boot": "Spring Boot",
        "quarkus": "Quarkus",
        "micronaut": "Micronaut"
    }

    def analyze_directory(self, root_path: str) -> DependencyAnalysisResult:
        """Inspects all manifest files inside root_path and produces an integrated dependency report."""
        detected_languages: Set[str] = set()
        detected_frameworks: Set[str] = set()
        package_managers: Set[str] = set()
        direct_deps: Dict[str, str] = {}
        dev_deps: Dict[str, str] = {}

        has_dockerfile = False
        has_docker_compose = False
        has_ci_workflows = False

        for current_root, dirs, files in os.walk(root_path):
            # Exclude ignored directories from walk
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"}]

            for file in files:
                f_lower = file.lower()
                full_path = os.path.join(current_root, file)

                # Check Docker & CI
                if f_lower == "dockerfile" or f_lower.endswith(".dockerfile"):
                    has_dockerfile = True
                elif f_lower in ("docker-compose.yml", "docker-compose.yaml"):
                    has_docker_compose = True
                elif ".github" in current_root and f_lower.endswith((".yml", ".yaml")):
                    has_ci_workflows = True

                # Check Python
                if f_lower == "requirements.txt" or f_lower.endswith(".requirements.txt"):
                    detected_languages.add("Python")
                    package_managers.add("pip")
                    self._parse_requirements_txt(full_path, direct_deps, detected_frameworks)
                elif f_lower == "pyproject.toml":
                    detected_languages.add("Python")
                    package_managers.add("poetry/pip")
                    self._parse_pyproject_toml(full_path, direct_deps, detected_frameworks)

                # Check JavaScript / TypeScript
                elif f_lower == "package.json":
                    detected_languages.add("JavaScript/TypeScript")
                    package_managers.add("npm")
                    self._parse_package_json(full_path, direct_deps, dev_deps, detected_frameworks)

                # Check Java
                elif f_lower == "pom.xml":
                    detected_languages.add("Java")
                    package_managers.add("Maven")
                elif f_lower in ("build.gradle", "build.gradle.kts"):
                    detected_languages.add("Java/Kotlin")
                    package_managers.add("Gradle")

                # Check C++
                elif f_lower in ("cmakelists.txt", "makefile"):
                    detected_languages.add("C/C++")
                    package_managers.add("CMake/Make")

        # Determine primary language
        primary = "General"
        if "Python" in detected_languages:
            primary = "Python"
        elif "JavaScript/TypeScript" in detected_languages:
            primary = "JavaScript/TypeScript"
        elif "Java" in detected_languages or "Java/Kotlin" in detected_languages:
            primary = "Java"
        elif "C/C++" in detected_languages:
            primary = "C++"

        return DependencyAnalysisResult(
            primary_language=primary,
            detected_languages=sorted(list(detected_languages)),
            detected_frameworks=sorted(list(detected_frameworks)),
            package_managers=sorted(list(package_managers)),
            direct_dependencies=direct_deps,
            dev_dependencies=dev_deps,
            has_dockerfile=has_dockerfile,
            has_docker_compose=has_docker_compose,
            has_ci_workflows=has_ci_workflows
        )

    def _parse_requirements_txt(self, path: str, direct_deps: Dict[str, str], frameworks: set):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    # Match package and version
                    m = re.match(r"^([A-Za-z0-9_\-]+)(?:([<>=~!]+.*))?", line)
                    if m:
                        pkg = m.group(1).lower()
                        ver = m.group(2) or "any"
                        direct_deps[pkg] = ver
                        if pkg in self.FRAMEWORK_RULES:
                            frameworks.add(self.FRAMEWORK_RULES[pkg])
        except Exception:
            pass

    def _parse_pyproject_toml(self, path: str, direct_deps: Dict[str, str], frameworks: set):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for line in content.splitlines():
                    m = re.match(r'^\s*([A-Za-z0-9_\-]+)\s*=\s*["\']([^"\']+)["\']', line)
                    if m:
                        pkg = m.group(1).lower()
                        ver = m.group(2)
                        direct_deps[pkg] = ver
                        if pkg in self.FRAMEWORK_RULES:
                            frameworks.add(self.FRAMEWORK_RULES[pkg])
        except Exception:
            pass

    def _parse_package_json(self, path: str, direct_deps: Dict[str, str], dev_deps: Dict[str, str], frameworks: set):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                for k, v in deps.items():
                    direct_deps[k] = str(v)
                    k_lower = k.lower()
                    if k_lower in self.FRAMEWORK_RULES:
                        frameworks.add(self.FRAMEWORK_RULES[k_lower])

                d_deps = data.get("devDependencies", {})
                for k, v in d_deps.items():
                    dev_deps[k] = str(v)
                    k_lower = k.lower()
                    if k_lower in self.FRAMEWORK_RULES:
                        frameworks.add(self.FRAMEWORK_RULES[k_lower])
        except Exception:
            pass


dependency_analyzer = DependencyAnalyzer()
