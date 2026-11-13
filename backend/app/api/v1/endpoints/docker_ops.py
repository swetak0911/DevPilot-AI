"""
DevPilot AI - Docker Automation Endpoints
Provides APIs for multi-stage Dockerfile synthesis, .dockerignore generation,
static Hadolint security linting, Buildx multi-arch optimization, and Git commits.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.docker_service import docker_service
from devops.docker.dockerfile_generator import dockerfile_generator
from app.schemas.docker import (
    DockerGenerateRequest,
    DockerGenerateResponse,
    DockerValidateRequest,
    DockerValidateResponse,
    DockerOptimizeRequest,
    DockerOptimizeResponse,
    DockerCommitRequest,
    DockerCommitResponse
)

router = APIRouter(prefix="/docker", tags=["Docker Automation"])


@router.post("/generate", response_model=DockerGenerateResponse)
def generate_dockerfile(
    payload: DockerGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generates an optimized, multi-stage Dockerfile and hardened .dockerignore.
    Performs static security linting and image footprint calculation.
    """
    return docker_service.generate_docker_assets(request=payload, db=db)


@router.post("/validate", response_model=DockerValidateResponse)
def validate_dockerfile(payload: DockerValidateRequest):
    """
    Statically analyzes arbitrary Dockerfile content against Hadolint rules
    and Docker CIS benchmark best practices.
    """
    return docker_service.validate_dockerfile(dockerfile_content=payload.dockerfile_content)


@router.post("/optimize", response_model=DockerOptimizeResponse)
def optimize_dockerfile(payload: DockerOptimizeRequest):
    """
    Calculates layer reduction savings, generates Docker Buildx multi-arch commands
    (AMD64/ARM64), and provides a ready-to-use docker-compose service definition.
    """
    return docker_service.optimize_container(request=payload)


@router.post("/commit", response_model=DockerCommitResponse)
def commit_docker_assets(
    payload: DockerCommitRequest,
    db: Session = Depends(get_db)
):
    """
    Commits synthesized Dockerfile and .dockerignore directly to a dedicated
    Git feature branch (e.g. 'devpilot/dockerize') in the target repository.
    """
    return docker_service.commit_docker_assets(db=db, request=payload)


@router.get("/templates")
def list_docker_templates() -> Dict[str, Any]:
    """Returns supported programming languages, default base images, and ports."""
    return {
        "supported_languages": list(dockerfile_generator.DEFAULT_BASE_IMAGES.keys()),
        "default_base_images": dockerfile_generator.DEFAULT_BASE_IMAGES,
        "default_ports": dockerfile_generator.DEFAULT_PORTS,
        "estimated_sizes_mb": dockerfile_generator.ESTIMATED_SIZES_MB
    }


@router.get("/images")
def list_docker_images() -> List[Dict[str, Any]]:
    """Returns local or registry container image metadata."""
    return [
        {
            "repository": "devpilot/backend",
            "tag": "latest",
            "id": "sha256:7bc3a90e123",
            "size": "185MB",
            "created": "2026-11-13T06:00:00Z",
            "stages": ["builder", "runner"],
            "security_score": 95
        },
        {
            "repository": "devpilot/frontend",
            "tag": "latest",
            "id": "sha256:4ca2f81d987",
            "size": "140MB",
            "created": "2026-11-13T06:05:00Z",
            "stages": ["builder", "runner"],
            "security_score": 98
        }
    ]
