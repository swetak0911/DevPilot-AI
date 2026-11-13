"""
DevPilot AI - Terraform Infrastructure as Code Intelligence Endpoints
Provides APIs for HCL parsing, terraform fmt formatting, static security scanning
(tfsec/Checkov rules), execution plan risk evaluation, and Human-in-the-Loop approval gates.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.infrastructure_service import infrastructure_service
from app.schemas.infrastructure import (
    TerraformFmtRequest,
    TerraformFmtResponse,
    TerraformAnalyseRequest,
    TerraformAnalyseResponse,
    TerraformPlanRequest,
    TerraformPlanResponse,
    TerraformApprovalRequest,
    TerraformApprovalResponse
)

router = APIRouter(prefix="/terraform", tags=["Terraform IaC Intelligence"])


@router.post("/fmt", response_model=TerraformFmtResponse)
def format_terraform_code(payload: TerraformFmtRequest):
    """
    Standardizes HCL formatting using 'terraform fmt' conventions:
    2-space indentation, alignment of '=' operators, and normalized whitespace.
    """
    return infrastructure_service.format_terraform(request=payload)


@router.post("/analyse", response_model=TerraformAnalyseResponse)
def analyse_terraform(
    payload: TerraformAnalyseRequest,
    db: Session = Depends(get_db)
):
    """
    Analyzes Terraform configurations for security flaws, hardcoded credentials,
    unrestricted ingress rules (0.0.0.0/0 on sensitive ports), and unencrypted volumes.
    """
    return infrastructure_service.analyse_terraform(request=payload, db=db)


@router.post("/validate")
def validate_terraform(content: Dict[str, str]):
    """Compatibility endpoint for rapid Terraform syntax and format check."""
    hcl = content.get("content") or content.get("hcl") or ""
    fmt_res = infrastructure_service.format_terraform(TerraformFmtRequest(hcl_content=hcl))
    ana_res = infrastructure_service.analyse_terraform(TerraformAnalyseRequest(hcl_content=hcl))
    return {
        "status": "SUCCESS" if ana_res.is_valid else "FAILED",
        "formatted": not fmt_res.is_formatted,
        "valid": ana_res.is_valid,
        "security_score": ana_res.security_score,
        "findings_count": len(ana_res.findings)
    }


@router.post("/plan", response_model=TerraformPlanResponse)
def preview_terraform_plan(payload: TerraformPlanRequest):
    """
    Evaluates Terraform execution plans, counts resources to add/change/destroy,
    detects destructive operations against stateful resources, and issues approval tokens.
    """
    return infrastructure_service.evaluate_plan(request=payload)


@router.post("/approve", response_model=TerraformApprovalResponse)
def submit_terraform_approval(payload: TerraformApprovalRequest):
    """
    Records an explicit Human-in-the-Loop approval decision for an execution plan.
    """
    return infrastructure_service.submit_approval(request=payload)
