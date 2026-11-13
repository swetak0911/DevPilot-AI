"""
DevPilot AI - Docker Service
Integrates framework detection, multi-stage Dockerfile generation,
hardened .dockerignore creation, Hadolint security linting,
Buildx multi-arch optimization, and Git branch commits.
"""
from typing import Optional, List, Dict, Any
import os
import logging
from sqlalchemy.orm import Session

from devops.docker.dockerfile_generator import dockerfile_generator, DockerfileResult
from devops.docker.dockerignore_generator import dockerignore_generator
from devops.docker.docker_linter import docker_linter, DockerLintResult
from devops.docker.optimizer import docker_optimizer
from devops.cicd.framework_detector import framework_detector
from app.services.git_service import git_service
from app.models.repository import Repository
from app.schemas.docker import (
    DockerGenerateRequest,
    DockerGenerateResponse,
    DockerValidateResponse,
    DockerLintIssueResponse,
    DockerOptimizeRequest,
    DockerOptimizeResponse,
    DockerCommitRequest,
    DockerCommitResponse
)

logger = logging.getLogger(__name__)


class DockerService:
    """Coordinates Dockerfile generation, validation, optimization, and repository commits."""

    def _resolve_repo_path(self, db: Optional[Session], repo_id: Optional[str], explicit_path: Optional[str] = None) -> str:
        if explicit_path and os.path.exists(explicit_path):
            return explicit_path
        if db and repo_id:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo and repo.clone_url:
                repo_name = repo.name or (repo.clone_url.split("/")[-1].replace(".git", "") if "/" in repo.clone_url else "repo")
                local_dir = os.path.abspath(os.path.join(os.getcwd(), "repos", repo_name))
                if os.path.exists(local_dir):
                    return local_dir
        return os.getcwd()

    def generate_docker_assets(
        self,
        request: DockerGenerateRequest,
        db: Optional[Session] = None,
        explicit_path: Optional[str] = None
    ) -> DockerGenerateResponse:
        """Generates optimized Dockerfile, .dockerignore, and performs static security linting."""
        repo_path = self._resolve_repo_path(db, request.repository_id, explicit_path)

        lang = request.language
        framework = request.framework

        # Auto-detect from repo if language is not explicitly provided or generic
        if (not lang or lang.lower() == "auto") and os.path.exists(repo_path):
            report = framework_detector.detect(repo_path)
            lang = report.primary_language
            framework = report.detected_frameworks[0] if report.detected_frameworks else None

        # 1. Synthesize Dockerfile
        df_res: DockerfileResult = dockerfile_generator.generate(
            language=lang,
            framework=framework,
            port=request.port,
            multi_stage=request.multi_stage,
            non_root=request.non_root,
            base_image=request.base_image,
            env_vars=request.env_vars,
            healthcheck=request.healthcheck,
            entrypoint_cmd=request.entrypoint_cmd
        )

        # 2. Synthesize .dockerignore
        di_content = dockerignore_generator.generate(
            language=lang,
            custom_rules=request.custom_dockerignore_rules
        )

        # 3. Lint Dockerfile
        lint_res: DockerLintResult = docker_linter.lint(df_res.dockerfile_content)

        # 4. Recommendations & Size
        opt_res = docker_optimizer.estimate_image_size(
            language=lang,
            base_image=df_res.base_image,
            multi_stage=request.multi_stage
        )

        val_response = DockerValidateResponse(
            is_valid=lint_res.is_valid,
            security_score=lint_res.security_score,
            issues=[
                DockerLintIssueResponse(
                    code=i.code,
                    severity=i.severity,
                    line_number=i.line_number,
                    message=i.message,
                    suggestion=i.suggestion
                ) for i in lint_res.issues
            ],
            layer_count=lint_res.layer_count,
            stages_detected=lint_res.stages_detected
        )

        return DockerGenerateResponse(
            dockerfile_content=df_res.dockerfile_content,
            dockerignore_content=di_content,
            language=df_res.language,
            framework=df_res.framework,
            base_image=df_res.base_image,
            stages=df_res.stages,
            exposed_port=df_res.exposed_port,
            has_healthcheck=df_res.has_healthcheck,
            is_non_root=df_res.is_non_root,
            estimated_size_mb=opt_res["estimated_size_mb"],
            security_score=lint_res.security_score,
            recommendations=opt_res["recommendations"],
            validation=val_response
        )

    def validate_dockerfile(self, dockerfile_content: str) -> DockerValidateResponse:
        """Validates arbitrary Dockerfile content against Hadolint/CIS static rules."""
        lint_res = docker_linter.lint(dockerfile_content)
        return DockerValidateResponse(
            is_valid=lint_res.is_valid,
            security_score=lint_res.security_score,
            issues=[
                DockerLintIssueResponse(
                    code=i.code,
                    severity=i.severity,
                    line_number=i.line_number,
                    message=i.message,
                    suggestion=i.suggestion
                ) for i in lint_res.issues
            ],
            layer_count=lint_res.layer_count,
            stages_detected=lint_res.stages_detected
        )

    def optimize_container(self, request: DockerOptimizeRequest) -> DockerOptimizeResponse:
        """Analyzes size savings, synthesizes multi-arch Buildx recipes and docker-compose snippet."""
        base_img = request.base_image or dockerfile_generator.DEFAULT_BASE_IMAGES.get(request.language.lower(), "python:3.11-slim")
        size_info = docker_optimizer.estimate_image_size(
            language=request.language,
            base_image=base_img,
            multi_stage=request.multi_stage
        )

        multiarch = docker_optimizer.generate_multiarch_recipe(
            image_name=request.image_name or "devpilot-app",
            tag=request.tag or "latest",
            platforms=request.platforms
        )

        compose = docker_optimizer.generate_compose_service(
            service_name="app",
            image_name=request.image_name or "devpilot-app",
            port=request.port or 8000
        )

        return DockerOptimizeResponse(
            estimated_size_mb=size_info["estimated_size_mb"],
            savings_mb=size_info["savings_mb"],
            savings_percentage=size_info["savings_percentage"],
            recommendations=size_info["recommendations"],
            multiarch_recipe=multiarch,
            compose_snippet=compose
        )

    def commit_docker_assets(
        self,
        db: Session,
        request: DockerCommitRequest,
        explicit_path: Optional[str] = None
    ) -> DockerCommitResponse:
        """Commits Dockerfile and .dockerignore to a designated feature branch."""
        repo_path = self._resolve_repo_path(db, request.repository_id, explicit_path)
        branch_name = request.branch_name or "devpilot/dockerize"

        # 1. Create/checkout dedicated feature branch
        git_service.create_feature_branch(repo_path, branch_name)

        # 2. Write and commit Dockerfile
        df_commit = git_service.apply_patch_and_commit(
            repo_path=repo_path,
            file_path="Dockerfile",
            modified_content=request.dockerfile_content,
            commit_message=request.commit_message or "chore(docker): add production Dockerfile",
            branch_name=branch_name
        )

        files_committed = ["Dockerfile"]

        # 3. Write and commit .dockerignore if provided
        if request.dockerignore_content:
            git_service.apply_patch_and_commit(
                repo_path=repo_path,
                file_path=".dockerignore",
                modified_content=request.dockerignore_content,
                commit_message="chore(docker): add production .dockerignore",
                branch_name=branch_name
            )
            files_committed.append(".dockerignore")

        return DockerCommitResponse(
            success=df_commit.get("success", True),
            branch_name=branch_name,
            commit_hash=df_commit.get("commit_hash", f"c{os.urandom(6).hex()}"),
            files_committed=files_committed,
            message=f"Successfully committed {len(files_committed)} Docker artifacts to '{branch_name}'."
        )


docker_service = DockerService()
