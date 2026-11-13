"""
========================================================================
 DevPilot AI - Phase 12 Docker Automation Agent Verification Suite
========================================================================
Statically and dynamically verifies multi-stage Dockerfile generation,
.dockerignore creation, Hadolint/CIS security linting, layer footprint
optimization, multi-arch recipe synthesis, and REST APIs.
========================================================================
"""
import sys
import os
import json
from typing import Dict, Any, List

# Add workspace and backend to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, SessionLocal
from devops.docker.dockerfile_generator import dockerfile_generator, DockerfileResult
from devops.docker.dockerignore_generator import dockerignore_generator
from devops.docker.docker_linter import docker_linter, DockerLintResult
from devops.docker.optimizer import docker_optimizer
from app.services.docker_service import docker_service
from app.schemas.docker import (
    DockerGenerateRequest,
    DockerValidateRequest,
    DockerOptimizeRequest,
    DockerCommitRequest
)


def run_phase12_verification() -> bool:
    print("=" * 72)
    print(" DevPilot AI - Phase 12 Docker Automation Agent Suite")
    print("=" * 72)

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Multi-Stage Hardened Dockerfile Generator (Python, Node, Go, Rust, Java)
        try:
            # 1.1 Python
            py_res = dockerfile_generator.generate("python", framework="FastAPI", port=8000, multi_stage=True, non_root=True)
            assert "AS builder" in py_res.dockerfile_content
            assert "AS runner" in py_res.dockerfile_content
            assert "USER appuser" in py_res.dockerfile_content
            assert "HEALTHCHECK" in py_res.dockerfile_content
            assert "EXPOSE 8000" in py_res.dockerfile_content

            # 1.2 Node.js
            node_res = dockerfile_generator.generate("nodejs", port=3000, multi_stage=True, non_root=True)
            assert "node:20-alpine" in node_res.dockerfile_content
            assert "npm ci" in node_res.dockerfile_content
            assert "USER nodejs" in node_res.dockerfile_content
            assert "EXPOSE 3000" in node_res.dockerfile_content

            # 1.3 Go
            go_res = dockerfile_generator.generate("go", port=8080, multi_stage=True, non_root=True)
            assert "golang:1.22-alpine" in go_res.dockerfile_content
            assert "CGO_ENABLED=0" in go_res.dockerfile_content
            assert "alpine:3.19" in go_res.dockerfile_content
            assert "USER appuser" in go_res.dockerfile_content

            # 1.4 Rust
            rust_res = dockerfile_generator.generate("rust", port=8080, multi_stage=True, non_root=True)
            assert "cargo build --release" in rust_res.dockerfile_content
            assert "debian:12-slim" in rust_res.dockerfile_content

            # 1.5 Java
            java_res = dockerfile_generator.generate("java", port=8080, multi_stage=True, non_root=True)
            assert "maven:3.9-eclipse-temurin-21" in java_res.dockerfile_content
            assert "eclipse-temurin:21-jre-alpine" in java_res.dockerfile_content

            print(f" [PASS] 1. Multi-Stage Dockerfile Generator: OK (Python, Node.js, Go, Rust, Java verified with non-root security)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Dockerfile Generator: {e}")

        # Check 2: Production-Grade .dockerignore Generator
        try:
            ignore_py = dockerignore_generator.generate("python", custom_rules=["temp_cache/"])
            assert ".git" in ignore_py
            assert ".env" in ignore_py
            assert "__pycache__/" in ignore_py
            assert "tests/" in ignore_py
            assert "temp_cache/" in ignore_py
            assert "*.key" in ignore_py
            assert "credentials.json" in ignore_py

            ignore_node = dockerignore_generator.generate("nodejs")
            assert "node_modules/" in ignore_node
            assert ".next/" in ignore_node

            print(f" [PASS] 2. Hardened .dockerignore Generator: OK (Excludes VCS, secrets, testing, and language build artifacts)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. .dockerignore Generator: {e}")

        # Check 3: Hadolint & CIS Container Security Linter
        try:
            # Bad Dockerfile with intentional violations
            bad_dockerfile = (
                "FROM python:latest\n"
                "COPY . .\n"
                "RUN pip install -r requirements.txt\n"
                "ENV SECRET_API_KEY=\"AKIA1234567890SECRETKEY\"\n"
                "RUN echo 'stage 1'\n"
                "RUN echo 'stage 2'\n"
                "EXPOSE 8000\n"
                "CMD [\"python\", \"main.py\"]\n"
            )

            lint_bad = docker_linter.lint(bad_dockerfile)
            codes = {iss.code for iss in lint_bad.issues}
            assert "DL3006" in codes, f"DL3006 not in {codes}"  # :latest unpinned tag
            assert "DL3002" in codes, f"DL3002 not in {codes}"  # missing USER (root execution)
            assert "DL3042" in codes, f"DL3042 not in {codes}"  # pip without --no-cache-dir
            assert "SEC101" in codes, f"SEC101 not in {codes}"  # hardcoded secret in ENV
            assert "SEC102" in codes, f"SEC102 not in {codes}"  # missing HEALTHCHECK
            assert "PERF101" in codes, f"PERF101 not in {codes}" # COPY . before dependency install
            assert lint_bad.is_valid is False, f"Expected invalid, got score {lint_bad.security_score}"
            assert lint_bad.security_score < 60, f"Expected score < 60, got {lint_bad.security_score}"

            # Good Dockerfile generated via DevPilot
            good_df = py_res.dockerfile_content
            lint_good = docker_linter.lint(good_df)
            assert lint_good.is_valid is True, f"Expected valid, got issues: {lint_good.issues}"
            assert lint_good.security_score >= 80, f"Expected score >= 80, got {lint_good.security_score}"

            print(f" [PASS] 3. Hadolint & CIS Container Security Linter: OK (Identified DL3002, DL3006, DL3042, SEC101, SEC102; Scored: {lint_good.security_score}/100)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. Container Security Linter: {type(e).__name__}: {e}")

        # Check 4: Layer Footprint Optimizer & Image Size Estimation
        try:
            py_opt = docker_optimizer.estimate_image_size("python", "python:3.11-slim", multi_stage=True)
            assert py_opt["estimated_size_mb"] < 250
            assert py_opt["savings_mb"] > 50
            assert py_opt["savings_percentage"] > 20
            assert len(py_opt["recommendations"]) >= 1

            go_opt = docker_optimizer.estimate_image_size("go", "golang:1.22-alpine", multi_stage=True)
            assert go_opt["estimated_size_mb"] < 50
            assert go_opt["savings_percentage"] > 80

            print(f" [PASS] 4. Layer Footprint Optimizer: OK (Python savings: {py_opt['savings_percentage']}%, Go savings: {go_opt['savings_percentage']}%)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Footprint Optimizer: {e}")

        # Check 5: Multi-Architecture Build Recipe & Compose Synthesizer
        try:
            recipe = docker_optimizer.generate_multiarch_recipe(
                image_name="devpilot/api",
                tag="v1.2.0",
                platforms=["linux/amd64", "linux/arm64"]
            )
            assert "linux/amd64,linux/arm64" in recipe["build_and_push_command"]
            assert "docker buildx create" in recipe["setup_commands"][0]
            assert "uses: docker/build-push-action@v6" in recipe["ci_step_snippet"]

            compose_snip = docker_optimizer.generate_compose_service(
                service_name="backend",
                image_name="devpilot/backend",
                port=8000,
                env_vars={"ENV": "production"}
            )
            assert "8000:8000" in compose_snip
            assert "restart: unless-stopped" in compose_snip
            assert "healthcheck:" in compose_snip

            print(f" [PASS] 5. Multi-Arch Build Recipe & Compose Synthesizer: OK (Buildx AMD64/ARM64, Compose service generated)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Multi-Arch & Compose Recipe: {e}")

        # Check 6: Dedicated Git Feature Branch Creation & Atomic Commit
        try:
            req_gen = DockerGenerateRequest(
                language="python",
                port=8000,
                multi_stage=True,
                non_root=True,
                repository_id="default-repo"
            )
            assets = docker_service.generate_docker_assets(req_gen, db=db, explicit_path=root_path)

            commit_req = DockerCommitRequest(
                repository_id="default-repo",
                branch_name="devpilot/dockerize-phase12-test",
                dockerfile_content=assets.dockerfile_content,
                dockerignore_content=assets.dockerignore_content,
                commit_message="chore(docker): configure production multi-stage Dockerfile and .dockerignore"
            )
            commit_res = docker_service.commit_docker_assets(db, commit_req, explicit_path=root_path)
            assert commit_res.success is True
            assert "devpilot/dockerize" in commit_res.branch_name
            assert "Dockerfile" in commit_res.files_committed
            assert ".dockerignore" in commit_res.files_committed
            assert len(commit_res.commit_hash) >= 6

            print(f" [PASS] 6. Git Feature Branch & Atomic Commit: OK (Branch: {commit_res.branch_name}, Commit: {commit_res.commit_hash}, Files: {commit_res.files_committed})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Git Branch & Commit: {e}")

        # Check 7: End-to-End REST APIs (/generate, /validate, /optimize, /commit, /templates)
        try:
            # 1. POST /api/docker/generate
            r_gen = client.post("/api/docker/generate", json={
                "language": "python",
                "framework": "FastAPI",
                "port": 8000,
                "multi_stage": True,
                "non_root": True
            })
            assert r_gen.status_code == 200, f"generate failed: {r_gen.text}"
            gen_data = r_gen.json()
            assert "dockerfile_content" in gen_data
            assert "dockerignore_content" in gen_data
            assert gen_data["validation"]["security_score"] >= 80

            # 2. POST /api/docker/validate
            r_val = client.post("/api/docker/validate", json={
                "dockerfile_content": gen_data["dockerfile_content"]
            })
            assert r_val.status_code == 200, f"validate failed: {r_val.text}"
            val_data = r_val.json()
            assert val_data["is_valid"] is True
            assert len(val_data["stages_detected"]) >= 2

            # 3. POST /api/docker/optimize
            r_opt = client.post("/api/docker/optimize", json={
                "language": "python",
                "base_image": "python:3.11-slim",
                "multi_stage": True,
                "port": 8000
            })
            assert r_opt.status_code == 200, f"optimize failed: {r_opt.text}"
            opt_data = r_opt.json()
            assert opt_data["savings_percentage"] > 0
            assert "multiarch_recipe" in opt_data

            # 4. POST /api/docker/commit
            r_com = client.post("/api/docker/commit", json={
                "repository_id": "default-repo",
                "branch_name": "devpilot/docker-api-veri",
                "dockerfile_content": gen_data["dockerfile_content"],
                "dockerignore_content": gen_data["dockerignore_content"]
            })
            assert r_com.status_code == 200, f"commit failed: {r_com.text}"
            com_data = r_com.json()
            assert com_data["success"] is True

            # 5. GET /api/docker/templates
            r_tpl = client.get("/api/docker/templates")
            assert r_tpl.status_code == 200
            assert "python" in r_tpl.json()["supported_languages"]

            print(f" [PASS] 7. End-to-End Docker REST APIs: OK (/generate, /validate, /optimize, /commit, /templates)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. Docker REST APIs: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 12 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks


if __name__ == "__main__":
    success = run_phase12_verification()
    sys.exit(0 if success else 1)
