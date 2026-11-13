"""
DevPilot AI - Docker Automation Subsystem
Multi-stage Dockerfile generation, .dockerignore creation, Hadolint security linter,
multi-arch build recipe synthesis, and image optimization.
"""
from devops.docker.dockerfile_generator import dockerfile_generator, DockerfileResult
from devops.docker.dockerignore_generator import dockerignore_generator
from devops.docker.docker_linter import docker_linter, DockerLintResult, DockerLintIssue
from devops.docker.optimizer import docker_optimizer

__all__ = [
    "dockerfile_generator",
    "DockerfileResult",
    "dockerignore_generator",
    "docker_linter",
    "DockerLintResult",
    "DockerLintIssue",
    "docker_optimizer",
]
