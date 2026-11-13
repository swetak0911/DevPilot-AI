"""API v1 Router Consolidation."""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    github,
    repositories,
    tasks,
    cicd,
    docker_ops,
    kubernetes_ops,
    terraform_ops,
    ml,
    analytics,
    monitoring,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(github.router)
api_router.include_router(repositories.router)
api_router.include_router(tasks.router)
api_router.include_router(cicd.router)
api_router.include_router(docker_ops.router)
api_router.include_router(kubernetes_ops.router)
api_router.include_router(terraform_ops.router)
api_router.include_router(ml.router)
api_router.include_router(analytics.router)
api_router.include_router(monitoring.router)
