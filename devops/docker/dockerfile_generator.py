"""
DevPilot AI - Multi-Stage Dockerfile Generator
Synthesizes hardened, production-grade, multi-stage Dockerfiles for Python, Node.js, Go, Rust, and Java.
Enforces non-root security privileges, layer caching, and healthcheck probes.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class DockerfileResult:
    dockerfile_content: str
    language: str
    framework: Optional[str]
    base_image: str
    stages: List[str]
    exposed_port: int
    has_healthcheck: bool
    is_non_root: bool
    estimated_size_mb: int


class DockerfileGenerator:
    """Generates optimized multi-stage Dockerfiles across multiple technology stacks."""

    DEFAULT_BASE_IMAGES = {
        "python": "python:3.11-slim",
        "nodejs": "node:20-alpine",
        "javascript": "node:20-alpine",
        "typescript": "node:20-alpine",
        "go": "golang:1.22-alpine",
        "rust": "rust:1.77-slim",
        "java": "eclipse-temurin:21-jre-alpine"
    }

    DEFAULT_PORTS = {
        "python": 8000,
        "nodejs": 3000,
        "javascript": 3000,
        "typescript": 3000,
        "go": 8080,
        "rust": 8080,
        "java": 8080
    }

    ESTIMATED_SIZES_MB = {
        "python": {"multi": 185, "single": 340},
        "nodejs": {"multi": 140, "single": 290},
        "javascript": {"multi": 140, "single": 290},
        "typescript": {"multi": 145, "single": 310},
        "go": {"multi": 25, "single": 450},
        "rust": {"multi": 45, "single": 650},
        "java": {"multi": 210, "single": 580}
    }

    def generate(
        self,
        language: str,
        framework: Optional[str] = None,
        port: Optional[int] = None,
        multi_stage: bool = True,
        non_root: bool = True,
        base_image: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        healthcheck: bool = True,
        entrypoint_cmd: Optional[str] = None
    ) -> DockerfileResult:
        """Synthesizes an optimized Dockerfile for the target language."""
        lang_key = (language or "python").lower()
        if lang_key not in self.DEFAULT_BASE_IMAGES:
            lang_key = "python"

        chosen_port = port or self.DEFAULT_PORTS.get(lang_key, 8000)
        chosen_base = base_image or self.DEFAULT_BASE_IMAGES[lang_key]

        if lang_key == "python":
            content, stages = self._generate_python(
                chosen_base, framework, chosen_port, multi_stage, non_root, env_vars, healthcheck, entrypoint_cmd
            )
        elif lang_key in ("nodejs", "javascript", "typescript"):
            content, stages = self._generate_node(
                chosen_base, framework, chosen_port, multi_stage, non_root, env_vars, healthcheck, entrypoint_cmd
            )
        elif lang_key == "go":
            content, stages = self._generate_go(
                chosen_base, framework, chosen_port, multi_stage, non_root, env_vars, healthcheck, entrypoint_cmd
            )
        elif lang_key == "rust":
            content, stages = self._generate_rust(
                chosen_base, framework, chosen_port, multi_stage, non_root, env_vars, healthcheck, entrypoint_cmd
            )
        elif lang_key == "java":
            content, stages = self._generate_java(
                chosen_base, framework, chosen_port, multi_stage, non_root, env_vars, healthcheck, entrypoint_cmd
            )
        else:
            content, stages = self._generate_python(
                chosen_base, framework, chosen_port, multi_stage, non_root, env_vars, healthcheck, entrypoint_cmd
            )

        sizes = self.ESTIMATED_SIZES_MB.get(lang_key, {"multi": 200, "single": 400})
        est_size = sizes["multi"] if multi_stage else sizes["single"]

        return DockerfileResult(
            dockerfile_content=content.strip() + "\n",
            language=lang_key,
            framework=framework,
            base_image=chosen_base,
            stages=stages,
            exposed_port=chosen_port,
            has_healthcheck=healthcheck,
            is_non_root=non_root,
            estimated_size_mb=est_size
        )

    def _render_env(self, env_vars: Optional[Dict[str, str]]) -> str:
        if not env_vars:
            return ""
        lines = []
        for k, v in env_vars.items():
            lines.append(f"ENV {k}=\"{v}\"")
        return "\n".join(lines) + "\n"

    def _generate_python(
        self, base: str, fw: Optional[str], port: int, multi: bool, non_root: bool,
        env_vars: Optional[Dict[str, str]], hc: bool, cmd_override: Optional[str]
    ) -> (str, List[str]):
        stages = ["builder", "runner"] if multi else ["runtime"]
        env_block = self._render_env(env_vars)

        default_cmd = f'["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "{port}"]'
        if cmd_override:
            default_cmd = f'["sh", "-c", "{cmd_override}"]'
        elif fw and "django" in fw.lower():
            default_cmd = f'["python", "manage.py", "runserver", "0.0.0.0:{port}"]'
        elif fw and "flask" in fw.lower():
            default_cmd = f'["flask", "run", "--host=0.0.0.0", "--port={port}"]'

        hc_block = ""
        if hc:
            hc_block = (
                f"HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\\n"
                f"  CMD python -c \"import urllib.request; urllib.request.urlopen('http://localhost:{port}/api/health')\" || exit 1\n\n"
            )

        if multi:
            content = f"""# ==============================================================================
# DevPilot AI - Multi-Stage Hardened Python Container
# Stage 1: Build dependency wheels
# ==============================================================================
FROM {base} AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    gcc \\
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# ==============================================================================
# Stage 2: Minimal runtime image
# ==============================================================================
FROM {base} AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PATH="/home/appuser/.local/bin:$PATH"
{env_block}
"""
            if non_root:
                content += """# Create non-root unprivileged user (UID 10001)
RUN groupadd -g 10001 appuser && \\
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser
"""
            else:
                content += """COPY --from=builder /root/.local /root/.local
COPY . .
"""

            content += f"""
EXPOSE {port}

{hc_block}CMD {default_cmd}
"""
        else:
            content = f"""FROM {base}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1
{env_block}
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
"""
            if non_root:
                content += """
RUN groupadd -g 10001 appuser && \\
    useradd -u 10001 -g appuser -m -s /bin/bash appuser && \\
    chown -R appuser:appuser /app

USER appuser
"""
            content += f"""
EXPOSE {port}

{hc_block}CMD {default_cmd}
"""
        return content, stages

    def _generate_node(
        self, base: str, fw: Optional[str], port: int, multi: bool, non_root: bool,
        env_vars: Optional[Dict[str, str]], hc: bool, cmd_override: Optional[str]
    ) -> (str, List[str]):
        stages = ["builder", "runner"] if multi else ["runtime"]
        env_block = self._render_env(env_vars)
        default_cmd = f'["node", "dist/index.js"]' if not cmd_override else f'["sh", "-c", "{cmd_override}"]'

        hc_block = ""
        if hc:
            hc_block = (
                f"HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\\n"
                f"  CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/health || exit 1\n\n"
            )

        if multi:
            content = f"""# ==============================================================================
# DevPilot AI - Multi-Stage Hardened Node.js Container
# Stage 1: Build dependencies & transpile
# ==============================================================================
FROM {base} AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY . .
RUN npm run build --if-present

# Prune devDependencies to keep production bundle lean
RUN npm prune --production

# ==============================================================================
# Stage 2: Ultra-lean production runtime
# ==============================================================================
FROM {base} AS runner

WORKDIR /app

ENV NODE_ENV=production
{env_block}
"""
            if non_root:
                content += """RUN addgroup -g 10001 -S nodejs && \\
    adduser -u 10001 -S nodejs -G nodejs

COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./package.json

USER nodejs
"""
            else:
                content += """COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./package.json
"""

            content += f"""
EXPOSE {port}

{hc_block}CMD {default_cmd}
"""
        else:
            content = f"""FROM {base}

WORKDIR /app

ENV NODE_ENV=production
{env_block}
COPY package*.json ./
RUN npm ci --only=production

COPY . .
"""
            if non_root:
                content += """RUN addgroup -g 10001 -S nodejs && adduser -u 10001 -S nodejs -G nodejs && chown -R nodejs:nodejs /app
USER nodejs
"""
            content += f"""
EXPOSE {port}

{hc_block}CMD {default_cmd}
"""
        return content, stages

    def _generate_go(
        self, base: str, fw: Optional[str], port: int, multi: bool, non_root: bool,
        env_vars: Optional[Dict[str, str]], hc: bool, cmd_override: Optional[str]
    ) -> (str, List[str]):
        stages = ["builder", "runner"] if multi else ["runtime"]
        env_block = self._render_env(env_vars)
        default_cmd = '["/app/server"]' if not cmd_override else f'["sh", "-c", "{cmd_override}"]'

        hc_block = ""
        if hc:
            hc_block = (
                f"HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\\n"
                f"  CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/health || exit 1\n\n"
            )

        if multi:
            content = f"""# ==============================================================================
# DevPilot AI - Multi-Stage Go Microservice
# Stage 1: Build static binary
# ==============================================================================
FROM {base} AS builder

WORKDIR /build

COPY go.mod go.sum* ./
RUN go mod download

COPY . .

# Compile static, stripped binary with zero CGO dependencies
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /build/server .

# ==============================================================================
# Stage 2: Minimal Alpine runtime
# ==============================================================================
FROM alpine:3.19 AS runner

WORKDIR /app

RUN apk --no-cache add ca-certificates tzdata
{env_block}
"""
            if non_root:
                content += """RUN addgroup -g 10001 -S appuser && \\
    adduser -u 10001 -S appuser -G appuser

COPY --from=builder --chown=appuser:appuser /build/server /app/server

USER appuser
"""
            else:
                content += "COPY --from=builder /build/server /app/server\n"

            content += f"""
EXPOSE {port}

{hc_block}ENTRYPOINT {default_cmd}
"""
        else:
            content = f"""FROM {base}

WORKDIR /app
{env_block}
COPY go.mod go.sum* ./
RUN go mod download

COPY . .
RUN go build -o server .

EXPOSE {port}
ENTRYPOINT {default_cmd}
"""
        return content, stages

    def _generate_rust(
        self, base: str, fw: Optional[str], port: int, multi: bool, non_root: bool,
        env_vars: Optional[Dict[str, str]], hc: bool, cmd_override: Optional[str]
    ) -> (str, List[str]):
        stages = ["builder", "runner"] if multi else ["runtime"]
        env_block = self._render_env(env_vars)
        default_cmd = '["/app/app"]' if not cmd_override else f'["sh", "-c", "{cmd_override}"]'

        hc_block = ""
        if hc:
            hc_block = (
                f"HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\\n"
                f"  CMD curl -f http://localhost:{port}/health || exit 1\n\n"
            )

        if multi:
            content = f"""# ==============================================================================
# DevPilot AI - Multi-Stage Hardened Rust Application
# Stage 1: Release compilation
# ==============================================================================
FROM {base} AS builder

WORKDIR /build

COPY Cargo.toml Cargo.lock* ./
COPY src/ ./src/

RUN cargo build --release

# ==============================================================================
# Stage 2: Distroless/Debian-slim runtime
# ==============================================================================
FROM debian:12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates \\
    curl \\
 && rm -rf /var/lib/apt/lists/*
{env_block}
"""
            if non_root:
                content += """RUN groupadd -g 10001 appuser && \\
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

COPY --from=builder --chown=appuser:appuser /build/target/release/app /app/app

USER appuser
"""
            else:
                content += "COPY --from=builder /build/target/release/app /app/app\n"

            content += f"""
EXPOSE {port}

{hc_block}ENTRYPOINT {default_cmd}
"""
        else:
            content = f"""FROM {base}

WORKDIR /app
{env_block}
COPY Cargo.toml Cargo.lock* ./
COPY src/ ./src/

RUN cargo build --release

EXPOSE {port}
ENTRYPOINT {default_cmd}
"""
        return content, stages

    def _generate_java(
        self, base: str, fw: Optional[str], port: int, multi: bool, non_root: bool,
        env_vars: Optional[Dict[str, str]], hc: bool, cmd_override: Optional[str]
    ) -> (str, List[str]):
        stages = ["builder", "runner"] if multi else ["runtime"]
        env_block = self._render_env(env_vars)
        default_cmd = '["java", "-jar", "/app/app.jar"]' if not cmd_override else f'["sh", "-c", "{cmd_override}"]'

        hc_block = ""
        if hc:
            hc_block = (
                f"HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\\n"
                f"  CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/actuator/health || exit 1\n\n"
            )

        if multi:
            content = f"""# ==============================================================================
# DevPilot AI - Multi-Stage Enterprise Java/Spring Container
# Stage 1: Maven Build
# ==============================================================================
FROM maven:3.9-eclipse-temurin-21 AS builder

WORKDIR /build

COPY pom.xml ./
RUN mvn dependency:go-offline -B

COPY src/ ./src/
RUN mvn package -DskipTests -B

# ==============================================================================
# Stage 2: Temurin JRE Alpine Runtime
# ==============================================================================
FROM {base} AS runner

WORKDIR /app

ENV JAVA_TOOL_OPTIONS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"
{env_block}
"""
            if non_root:
                content += """RUN addgroup -g 10001 -S appuser && \\
    adduser -u 10001 -S appuser -G appuser

COPY --from=builder --chown=appuser:appuser /build/target/*.jar /app/app.jar

USER appuser
"""
            else:
                content += "COPY --from=builder /build/target/*.jar /app/app.jar\n"

            content += f"""
EXPOSE {port}

{hc_block}ENTRYPOINT {default_cmd}
"""
        else:
            content = f"""FROM {base}

WORKDIR /app
{env_block}
COPY target/*.jar /app/app.jar

EXPOSE {port}
ENTRYPOINT {default_cmd}
"""
        return content, stages


dockerfile_generator = DockerfileGenerator()
