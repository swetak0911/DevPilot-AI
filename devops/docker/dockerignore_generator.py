"""
DevPilot AI - .dockerignore File Generator
Generates hardened .dockerignore files eliminating build context bloat,
protecting credentials and secret keys, and avoiding layer cache invalidation.
"""
from typing import Optional, List


class DockerignoreGenerator:
    """Generates structured, security-hardened .dockerignore configurations."""

    COMMON_SECTIONS = {
        "VCS & Repositories": [
            ".git",
            ".gitignore",
            ".gitattributes",
            ".github",
            ".gitlab-ci.yml",
            ".hg",
            ".svn"
        ],
        "Secrets & Private Credentials": [
            ".env",
            ".env.*",
            "!.env.example",
            "*.pem",
            "*.key",
            "*.crt",
            "*.p12",
            "*.pfx",
            "id_rsa*",
            "id_ed25519*",
            "credentials.json",
            "service-account*.json",
            ".aws/",
            ".azure/"
        ],
        "Docker & CI/CD Configuration": [
            "Dockerfile*",
            "docker-compose*",
            ".dockerignore",
            ".devcontainer"
        ],
        "Documentation & Test Artifacts": [
            "docs/",
            "*.md",
            "LICENSE*",
            "tests/",
            "test/",
            "spec/",
            "coverage/",
            ".coverage",
            "htmlcov/"
        ],
        "OS & Editor Metadata": [
            ".DS_Store",
            "Thumbs.db",
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            "*~"
        ]
    }

    LANGUAGE_SECTIONS = {
        "python": [
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            ".tox/",
            ".venv/",
            "venv/",
            "env/",
            "ENV/",
            "*.egg-info/",
            "dist/",
            "build/",
            "*.log"
        ],
        "nodejs": [
            "node_modules/",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
            "pnpm-debug.log*",
            ".next/",
            ".nuxt/",
            ".turbo/",
            "dist/",
            "build/",
            ".parcel-cache/",
            "*.tsbuildinfo"
        ],
        "javascript": [
            "node_modules/",
            "npm-debug.log*",
            "yarn-debug.log*",
            "dist/",
            "build/"
        ],
        "typescript": [
            "node_modules/",
            "dist/",
            "build/",
            "*.tsbuildinfo",
            ".turbo/"
        ],
        "go": [
            "bin/",
            "pkg/",
            "*.exe",
            "*.exe~",
            "*.dll",
            "*.so",
            "*.dylib",
            "*.test",
            "*.out"
        ],
        "rust": [
            "target/",
            "**/*.rs.bk",
            "Cargo.lock"  # If relying on vendor
        ],
        "java": [
            "target/",
            "build/",
            ".gradle/",
            "*.class",
            "*.jar",
            "*.war",
            "*.ear"
        ]
    }

    def generate(
        self,
        language: str = "python",
        custom_rules: Optional[List[str]] = None
    ) -> str:
        """Generates a categorized .dockerignore file tailored to the target tech stack."""
        lang_key = (language or "python").lower()
        output = [
            "# ==============================================================================",
            "# DevPilot AI - Production .dockerignore Configuration",
            f"# Tech Stack: {lang_key.capitalize()}",
            "# ==============================================================================\n"
        ]

        # Common security and system sections
        for section_title, patterns in self.COMMON_SECTIONS.items():
            output.append(f"# --- {section_title} ---")
            output.extend(patterns)
            output.append("")

        # Language specific patterns
        lang_patterns = self.LANGUAGE_SECTIONS.get(lang_key, self.LANGUAGE_SECTIONS["python"])
        output.append(f"# --- {lang_key.capitalize()} Build & Runtime Artifacts ---")
        output.extend(lang_patterns)
        output.append("")

        # Custom user exclusions
        if custom_rules:
            output.append("# --- Custom Project Exclusions ---")
            output.extend(custom_rules)
            output.append("")

        return "\n".join(output).strip() + "\n"


dockerignore_generator = DockerignoreGenerator()
