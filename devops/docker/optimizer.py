"""
DevPilot AI - Docker Optimizer & Multi-Arch Build Recipe Synthesizer
Calculates image size estimates, analyzes layer footprint reductions,
and generates Docker Buildx multi-architecture recipes for AMD64/ARM64.
"""
from typing import Dict, Any, List, Optional


class DockerOptimizer:
    """Provides container footprint optimization, layer analysis, and multi-arch recipes."""

    BASE_IMAGE_METRICS = {
        "python:3.11-slim": {"base_mb": 125, "builder_overhead_mb": 180, "avg_deps_mb": 60},
        "python:3.12-slim": {"base_mb": 130, "builder_overhead_mb": 180, "avg_deps_mb": 60},
        "python:3.11-alpine": {"base_mb": 50, "builder_overhead_mb": 220, "avg_deps_mb": 65},
        "node:20-alpine": {"base_mb": 135, "builder_overhead_mb": 150, "avg_deps_mb": 55},
        "node:20-slim": {"base_mb": 190, "builder_overhead_mb": 170, "avg_deps_mb": 60},
        "golang:1.22-alpine": {"base_mb": 260, "builder_overhead_mb": 350, "avg_deps_mb": 15},
        "alpine:3.19": {"base_mb": 7, "builder_overhead_mb": 0, "avg_deps_mb": 18},
        "rust:1.77-slim": {"base_mb": 850, "builder_overhead_mb": 500, "avg_deps_mb": 35},
        "debian:12-slim": {"base_mb": 75, "builder_overhead_mb": 0, "avg_deps_mb": 25},
        "maven:3.9-eclipse-temurin-21": {"base_mb": 500, "builder_overhead_mb": 350, "avg_deps_mb": 40},
        "eclipse-temurin:21-jre-alpine": {"base_mb": 180, "builder_overhead_mb": 0, "avg_deps_mb": 30}
    }

    def estimate_image_size(
        self,
        language: str,
        base_image: str,
        multi_stage: bool = True
    ) -> Dict[str, Any]:
        """Calculates estimated uncompressed container size and footprint reductions."""
        lang_key = (language or "python").lower()
        metrics = self.BASE_IMAGE_METRICS.get(base_image)
        if not metrics:
            metrics = {"base_mb": 140, "builder_overhead_mb": 160, "avg_deps_mb": 50}

        base_mb = metrics["base_mb"]
        builder_overhead = metrics["builder_overhead_mb"]
        deps_mb = metrics["avg_deps_mb"]

        if multi_stage:
            runtime_base = base_mb
            if lang_key == "go":
                runtime_base = 7  # alpine
            elif lang_key == "rust":
                runtime_base = 75  # debian-slim
            elif lang_key == "java":
                runtime_base = 180  # jre-alpine

            total_size_mb = runtime_base + deps_mb
            single_size_mb = base_mb + builder_overhead + deps_mb
            savings_mb = max(0, single_size_mb - total_size_mb)
            savings_pct = round((savings_mb / single_size_mb) * 100, 1) if single_size_mb else 0
        else:
            total_size_mb = base_mb + builder_overhead + deps_mb
            savings_mb = 0
            savings_pct = 0.0

        recommendations = []
        if multi_stage:
            recommendations.append(f"Multi-stage build saves ~{savings_mb}MB ({savings_pct}% reduction) by pruning compiler toolchains.")
        else:
            recommendations.append("Switch to a multi-stage Dockerfile to eliminate build dependencies from runtime.")

        if "alpine" in base_image:
            recommendations.append("Alpine Linux runtime selected for minimal footprint and low CVE surface.")
        elif "slim" in base_image:
            recommendations.append("Slim Debian runtime selected for balanced compatibility with glibc C-extensions.")

        return {
            "language": lang_key,
            "base_image": base_image,
            "multi_stage": multi_stage,
            "estimated_size_mb": total_size_mb,
            "savings_mb": savings_mb,
            "savings_percentage": savings_pct,
            "recommendations": recommendations
        }

    def generate_multiarch_recipe(
        self,
        image_name: str,
        tag: str = "latest",
        platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Synthesizes Docker Buildx commands for multi-architecture (AMD64 & ARM64) distribution."""
        selected_platforms = platforms or ["linux/amd64", "linux/arm64"]
        platform_str = ",".join(selected_platforms)
        builder_name = "devpilot-builder"

        return {
            "image_name": image_name,
            "tag": tag,
            "platforms": selected_platforms,
            "builder_name": builder_name,
            "setup_commands": [
                f"docker buildx create --name {builder_name} --driver docker-container --use",
                "docker buildx inspect --bootstrap"
            ],
            "build_and_push_command": (
                f"docker buildx build --platform {platform_str} "
                f"-t {image_name}:{tag} --push ."
            ),
            "build_local_command": (
                f"docker buildx build --platform linux/amd64 "
                f"-t {image_name}:{tag} --load ."
            ),
            "ci_step_snippet": (
                "- name: Set up QEMU\n"
                "  uses: docker/setup-qemu-action@v3\n\n"
                "- name: Set up Docker Buildx\n"
                "  uses: docker/setup-buildx-action@v3\n\n"
                "- name: Build and push multi-arch image\n"
                "  uses: docker/build-push-action@v6\n"
                "  with:\n"
                "    context: .\n"
                f"    platforms: {platform_str}\n"
                "    push: true\n"
                f"    tags: {image_name}:{tag}\n"
            )
        }

    def generate_compose_service(
        self,
        service_name: str,
        image_name: str,
        port: int = 8000,
        env_vars: Optional[Dict[str, str]] = None
    ) -> str:
        """Generates a docker-compose.yml service snippet."""
        env_section = ""
        if env_vars:
            env_lines = ["      environment:"]
            for k, v in env_vars.items():
                env_lines.append(f'        - {k}="{v}"')
            env_section = "\n".join(env_lines) + "\n"

        return f"""  {service_name}:
    build:
      context: .
      dockerfile: Dockerfile
    image: {image_name}:latest
    container_name: {service_name}
    ports:
      - "{port}:{port}"
    restart: unless-stopped
{env_section}    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:{port}/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
"""


docker_optimizer = DockerOptimizer()
