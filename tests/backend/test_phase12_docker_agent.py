"""
DevPilot AI - Phase 12 Docker Automation Tests
Tests multi-stage Dockerfile generation, .dockerignore creation,
Hadolint security linting, image optimization, and REST API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, SessionLocal
from devops.docker.dockerfile_generator import dockerfile_generator
from devops.docker.dockerignore_generator import dockerignore_generator
from devops.docker.docker_linter import docker_linter
from devops.docker.optimizer import docker_optimizer
from app.services.docker_service import docker_service
from app.schemas.docker import (
    DockerGenerateRequest,
    DockerValidateRequest,
    DockerOptimizeRequest,
    DockerCommitRequest
)


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_dockerfile_generator_python():
    # Multi-stage
    res_multi = dockerfile_generator.generate(
        language="python",
        framework="FastAPI",
        port=8000,
        multi_stage=True,
        non_root=True,
        healthcheck=True
    )
    assert res_multi.language == "python"
    assert "AS builder" in res_multi.dockerfile_content
    assert "AS runner" in res_multi.dockerfile_content
    assert "USER appuser" in res_multi.dockerfile_content
    assert "HEALTHCHECK" in res_multi.dockerfile_content
    assert "EXPOSE 8000" in res_multi.dockerfile_content
    assert "PYTHONDONTWRITEBYTECODE=1" in res_multi.dockerfile_content
    assert res_multi.estimated_size_mb < 250

    # Single-stage
    res_single = dockerfile_generator.generate(
        language="python",
        port=8000,
        multi_stage=False
    )
    assert "AS builder" not in res_single.dockerfile_content
    assert "EXPOSE 8000" in res_single.dockerfile_content


def test_dockerfile_generator_multi_languages():
    # Node.js
    res_node = dockerfile_generator.generate(language="nodejs", port=3000)
    assert "node:20-alpine" in res_node.dockerfile_content
    assert "npm ci" in res_node.dockerfile_content
    assert "USER nodejs" in res_node.dockerfile_content
    assert "EXPOSE 3000" in res_node.dockerfile_content

    # Go
    res_go = dockerfile_generator.generate(language="go", port=8080)
    assert "golang:1.22-alpine" in res_go.dockerfile_content
    assert "CGO_ENABLED=0" in res_go.dockerfile_content
    assert "alpine:3.19" in res_go.dockerfile_content
    assert "USER appuser" in res_go.dockerfile_content

    # Rust
    res_rust = dockerfile_generator.generate(language="rust", port=8080)
    assert "rust:1.77-slim" in res_rust.dockerfile_content
    assert "cargo build --release" in res_rust.dockerfile_content
    assert "debian:12-slim" in res_rust.dockerfile_content

    # Java
    res_java = dockerfile_generator.generate(language="java", port=8080)
    assert "maven:3.9-eclipse-temurin-21" in res_java.dockerfile_content
    assert "eclipse-temurin:21-jre-alpine" in res_java.dockerfile_content
    assert "JAVA_TOOL_OPTIONS" in res_java.dockerfile_content


def test_dockerignore_generator():
    ignore = dockerignore_generator.generate(language="python", custom_rules=["temp_artifacts/"])
    assert ".git" in ignore
    assert ".env" in ignore
    assert "__pycache__/" in ignore
    assert "tests/" in ignore
    assert "temp_artifacts/" in ignore

    node_ignore = dockerignore_generator.generate(language="nodejs")
    assert "node_modules/" in ignore or "node_modules/" in node_ignore
    assert ".next/" in node_ignore


def test_docker_linter_hadolint_rules():
    # Vulnerable Dockerfile
    vuln_df = """FROM python:latest
COPY . .
RUN pip install -r requirements.txt
ENV DATABASE_PASSWORD="super-secret-password-123456"
RUN echo "building"
RUN echo "building again"
EXPOSE 8000
CMD ["python", "app.py"]
"""
    res = docker_linter.lint(vuln_df)
    codes = [i.code for i in res.issues]
    assert "DL3006" in codes  # :latest tag
    assert "DL3002" in codes  # missing USER (root)
    assert "DL3042" in codes  # pip install without --no-cache-dir
    assert "SEC101" in codes  # hardcoded password in ENV
    assert "SEC102" in codes  # missing HEALTHCHECK
    assert "PERF101" in codes # COPY . before pip install
    assert res.is_valid is False
    assert res.security_score < 60

    # Hardened Dockerfile
    good_df = dockerfile_generator.generate(language="python", multi_stage=True, non_root=True).dockerfile_content
    good_res = docker_linter.lint(good_df)
    assert good_res.is_valid is True
    assert good_res.security_score >= 80


def test_docker_optimizer():
    # Size calculation
    size_res = docker_optimizer.estimate_image_size(language="python", base_image="python:3.11-slim", multi_stage=True)
    assert size_res["estimated_size_mb"] > 0
    assert size_res["savings_mb"] > 0
    assert size_res["savings_percentage"] > 20

    # Multi-arch Buildx recipe
    recipe = docker_optimizer.generate_multiarch_recipe(image_name="devpilot/api", tag="v1.0.0")
    assert "linux/amd64,linux/arm64" in recipe["build_and_push_command"]
    assert "docker buildx create" in recipe["setup_commands"][0]

    # Compose snippet
    compose = docker_optimizer.generate_compose_service("api", "devpilot/api", port=8000)
    assert "ports:" in compose
    assert "8000:8000" in compose


def test_docker_service_full_workflow(db):
    req = DockerGenerateRequest(
        language="python",
        port=8000,
        multi_stage=True,
        non_root=True
    )
    gen_res = docker_service.generate_docker_assets(req, db=db)
    assert gen_res.is_non_root is True
    assert len(gen_res.stages) == 2
    assert gen_res.validation.security_score >= 80

    commit_req = DockerCommitRequest(
        repository_id="default-repo",
        branch_name="devpilot/docker-test",
        dockerfile_content=gen_res.dockerfile_content,
        dockerignore_content=gen_res.dockerignore_content
    )
    commit_res = docker_service.commit_docker_assets(db, commit_req)
    assert commit_res.success is True
    assert "devpilot/docker-test" in commit_res.branch_name
    assert "Dockerfile" in commit_res.files_committed
    assert ".dockerignore" in commit_res.files_committed


def test_docker_rest_apis(client):
    # 1. POST /api/docker/generate
    res_gen = client.post("/api/docker/generate", json={
        "language": "nodejs",
        "port": 3000,
        "multi_stage": True,
        "non_root": True
    })
    assert res_gen.status_code == 200
    data_gen = res_gen.json()
    assert data_gen["language"] == "nodejs"
    assert "node:20-alpine" in data_gen["dockerfile_content"]
    assert data_gen["validation"]["is_valid"] is True

    # 2. POST /api/docker/validate
    res_val = client.post("/api/docker/validate", json={
        "dockerfile_content": data_gen["dockerfile_content"]
    })
    assert res_val.status_code == 200
    data_val = res_val.json()
    assert data_val["security_score"] >= 80

    # 3. POST /api/docker/optimize
    res_opt = client.post("/api/docker/optimize", json={
        "language": "nodejs",
        "port": 3000,
        "multi_stage": True
    })
    assert res_opt.status_code == 200
    data_opt = res_opt.json()
    assert "multiarch_recipe" in data_opt
    assert "compose_snippet" in data_opt

    # 4. POST /api/docker/commit
    res_com = client.post("/api/docker/commit", json={
        "repository_id": "default-repo",
        "branch_name": "devpilot/docker-api-test",
        "dockerfile_content": data_gen["dockerfile_content"],
        "dockerignore_content": data_gen["dockerignore_content"]
    })
    assert res_com.status_code == 200
    data_com = res_com.json()
    assert data_com["success"] is True

    # 5. GET /api/docker/templates
    res_tpl = client.get("/api/docker/templates")
    assert res_tpl.status_code == 200
    assert "python" in res_tpl.json()["supported_languages"]
