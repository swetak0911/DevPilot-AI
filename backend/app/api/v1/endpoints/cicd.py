"""CI/CD Generation and Failure Intelligence Endpoints."""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.cicd import WorkflowRun
from app.schemas.cicd import (
    WorkflowGenerateRequest,
    WorkflowGenerateResponse,
    WorkflowRunResponse,
    CIAnalysisResponse,
    FrameworkDetectRequest,
    FrameworkDetectResponse,
    WorkflowValidateRequest,
    WorkflowValidateResponse,
    WorkflowCommitRequest,
    WorkflowCommitResponse,
    WorkflowDispatchTriggerRequest,
    CIRemediateRequest,
    CIRemediateResponse,
    CILogParseRequest,
    CILogParseResponse
)
from app.services.cicd_service import cicd_service
from app.services.ci_intelligence_service import ci_intelligence_service

router = APIRouter(prefix="/cicd", tags=["CI/CD & DevOps Intelligence"])


@router.post("/detect-framework/{repo_id}", response_model=FrameworkDetectResponse)
def detect_repo_framework(repo_id: str, db: Session = Depends(get_db)):
    """Scans repository files and discovers language runtimes, test frameworks, and linters."""
    return cicd_service.detect_framework(db, repo_id=repo_id)


@router.post("/generate", response_model=WorkflowGenerateResponse)
def generate_cicd_workflow(payload: WorkflowGenerateRequest, db: Session = Depends(get_db)):
    """Analyzes repository framework and produces a validated GitHub Actions workflow."""
    return cicd_service.generate_workflow(db, payload)


@router.post("/validate-workflow", response_model=WorkflowValidateResponse)
def validate_workflow(payload: WorkflowValidateRequest):
    """Validates GitHub Actions syntax, structural schema, and checks for deprecated actions."""
    return cicd_service.validate_workflow_yaml(payload.workflow_yaml)


@router.post("/commit-workflow", response_model=WorkflowCommitResponse)
def commit_workflow(payload: WorkflowCommitRequest, db: Session = Depends(get_db)):
    """Commits workflow YAML to a dedicated feature branch in the repository."""
    return cicd_service.commit_workflow(db, payload)


@router.post("/trigger-run/{repo_id}", response_model=WorkflowRunResponse)
def trigger_workflow_run(
    repo_id: str,
    payload: Optional[WorkflowDispatchTriggerRequest] = Body(default=None),
    db: Session = Depends(get_db)
):
    """Dispatches a new CI/CD workflow run and tracks job step execution."""
    if payload is None:
        payload = WorkflowDispatchTriggerRequest(
            repository_id=repo_id,
            workflow_name="DevPilot Continuous Integration",
            branch_name="main"
        )
    else:
        payload.repository_id = repo_id
    return cicd_service.trigger_workflow_run(db, payload)


@router.get("/workflows")
def list_workflows(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Lists configured workflow definitions."""
    return [
        {
            "id": "wf-1",
            "name": "DevPilot Continuous Integration",
            "path": ".github/workflows/ci.yml",
            "state": "active",
            "badge_url": "https://img.shields.io/badge/CI-passing-brightgreen"
        }
    ]


@router.get("/runs", response_model=List[WorkflowRunResponse])
def list_workflow_runs(repository_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Lists recent GitHub Actions pipeline runs."""
    return cicd_service.list_workflow_runs(db, repository_id=repository_id)


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
def get_workflow_run(run_id: str, db: Session = Depends(get_db)):
    """Retrieves details of a specific CI run."""
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.post("/runs/{run_id}/analyse", response_model=CIAnalysisResponse)
def analyze_workflow_failure(
    run_id: str,
    raw_logs: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db)
):
    """Diagnoses root cause of pipeline failures using log analysis, categorization, and RAG."""
    return ci_intelligence_service.diagnose_run(db, run_id=run_id, raw_logs=raw_logs)


@router.post("/runs/{run_id}/remediate", response_model=CIRemediateResponse)
def remediate_workflow_failure(
    run_id: str,
    payload: Optional[CIRemediateRequest] = None,
    db: Session = Depends(get_db)
):
    """Applies automated remediation patch for a failed CI run on a dedicated branch."""
    if payload is None:
        payload = CIRemediateRequest(run_id=run_id)
    else:
        payload.run_id = run_id
    return ci_intelligence_service.remediate_run(db, payload)


@router.post("/logs/parse", response_model=CILogParseResponse)
def parse_ci_logs(payload: CILogParseRequest):
    """Directly parses raw CI console logs and returns error classification & suggested fix."""
    return ci_intelligence_service.parse_and_diagnose_logs(payload)
