"""
DevPilot AI - Kubernetes Automation Endpoints
Provides APIs for Kubernetes manifest generation (Deployment, Service, ConfigMap, HPA, Ingress),
OpenAPI schema validation, Pod Security Standards checking, and Git commits.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.infrastructure_service import infrastructure_service
from app.schemas.infrastructure import (
    K8sGenerateRequest,
    K8sGenerateResponse,
    K8sValidateRequest,
    K8sValidateResponse,
    K8sCommitRequest,
    K8sCommitResponse
)

router = APIRouter(prefix="/kubernetes", tags=["Kubernetes Automation"])


@router.post("/generate", response_model=K8sGenerateResponse)
def generate_kubernetes_manifests(
    payload: K8sGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Synthesizes hardened Kubernetes manifests including Deployment with Pod Security Standards
    (Restricted profile), ClusterIP/LoadBalancer Service, ConfigMap, HPA, and Ingress.
    """
    return infrastructure_service.generate_k8s_manifests(request=payload, db=db)


@router.post("/validate", response_model=K8sValidateResponse)
def validate_kubernetes_manifests(payload: K8sValidateRequest):
    """
    Validates single or multi-document Kubernetes YAML against OpenAPI schema rules,
    resource constraints (limits >= requests), port bounds, and CIS security benchmarks.
    """
    return infrastructure_service.validate_k8s_manifests(request=payload)


@router.post("/commit", response_model=K8sCommitResponse)
def commit_kubernetes_manifests(
    payload: K8sCommitRequest,
    db: Session = Depends(get_db)
):
    """
    Commits synthesized Kubernetes YAML manifests directly to a dedicated
    Git feature branch (e.g., 'devpilot/k8s-manifests').
    """
    return infrastructure_service.commit_k8s_manifests(db=db, request=payload)
