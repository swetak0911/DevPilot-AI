"""Task Execution Schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.task import TaskStatus, TaskType


class TaskCreate(BaseModel):
    repository_id: str
    title: str = Field(..., min_length=3, max_length=255)
    instruction: str = Field(..., min_length=10)
    task_type: TaskType = TaskType.BUG_FIX


class TaskStepResponse(BaseModel):
    id: str
    step_order: int
    agent_name: str
    description: str
    status: str
    tool_calls: List[Dict[str, Any]] = []
    output_summary: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CodePatchResponse(BaseModel):
    id: str
    file_path: str
    original_content: str
    modified_content: str
    unified_diff: str
    is_approved: str
    created_at: datetime

    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    id: str
    attempt_number: int
    passed: int
    failed: int
    errors: int
    exit_code: int
    stdout: str
    stderr: str
    failure_details: List[Dict[str, Any]] = []
    executed_at: datetime

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    id: str
    task_id: str
    summary: str
    findings: List[Dict[str, Any]] = []
    decision: str
    score: Optional[float] = 8.5
    risk_level: Optional[str] = "LOW"
    reviewed_at: datetime

    class Config:
        from_attributes = True


class ReviewCreateRequest(BaseModel):
    override_instructions: Optional[str] = None


class PullRequestCreateRequest(BaseModel):
    branch_name: Optional[str] = None
    base_branch: Optional[str] = "main"
    title: Optional[str] = None
    body: Optional[str] = None


class PullRequestResponse(BaseModel):
    id: str
    pr_number: Optional[int] = None
    title: str
    body: str
    branch_name: str
    base_branch: str
    html_url: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    repository_id: str
    title: str
    instruction: str
    task_type: TaskType
    status: TaskStatus
    execution_plan: List[Dict[str, Any]] = []
    active_agent: Optional[str] = None
    repair_attempt_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    steps: List[TaskStepResponse] = []
    patches: List[CodePatchResponse] = []
    test_results: List[TestResultResponse] = []
    review: Optional[ReviewResponse] = None
    pull_request: Optional[PullRequestResponse] = None

    class Config:
        from_attributes = True


class TaskApprovalRequest(BaseModel):
    approved: bool
    comments: Optional[str] = None


class PatchValidationRequest(BaseModel):
    file_path: str = "file.py"
    original_content: str
    unified_diff: str


class PatchValidationResponse(BaseModel):
    is_valid: bool
    hunk_count: int
    errors: List[str] = []
    syntax_valid: bool = True


class OrchestrateTaskRequest(BaseModel):
    human_approval_required: bool = True
    max_repair_attempts: int = 3


class ResumeWorkflowRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None

