"""
DevPilot AI - Orchestration Service
Bridges FastAPI endpoints with the LangGraph Workflow Orchestrator,
synchronizing task state, steps, patches, checkpoints, and human approval gates.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import os
import logging
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStep, CodePatch, TestResult, TaskCheckpoint, TaskStatus
from app.models.repository import Repository
from app.services.repository_service import repository_service
from ai_engine.orchestration.workflow_orchestrator import workflow_orchestrator
from ai_engine.orchestration.checkpoint_manager import checkpoint_manager
from ai_engine.orchestration.agent_state import AgentState, serialize_agent_state

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Service orchestrating LangGraph multi-agent execution and database synchronizations."""

    @staticmethod
    def start_orchestrated_workflow(
        db: Session,
        task_id: str,
        human_approval_required: bool = True,
        max_repair_attempts: int = 3
    ) -> Dict[str, Any]:
        """Launches the full LangGraph multi-agent pipeline for a task."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        repo = db.query(Repository).filter(Repository.id == task.repository_id).first()
        repo_name = repo.name if repo else "DevPilot-Workspace"
        repo_path = repository_service.get_repository_workspace_path(repo) if repo else "."

        # Update initial task status
        task.status = TaskStatus.RUNNING
        task.error_message = None
        db.commit()

        # Execute LangGraph workflow
        state: AgentState = workflow_orchestrator.run_workflow(
            task_id=task.id,
            instruction=task.instruction,
            repo_name=repo_name,
            repo_path=repo_path,
            task_type=task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type),
            max_repair_attempts=max_repair_attempts,
            human_approval_required=human_approval_required
        )

        # Synchronize execution state with DB
        OrchestrationService._sync_state_to_db(db, task, state)
        return serialize_agent_state(state)

    @staticmethod
    def resume_orchestrated_workflow(
        db: Session,
        task_id: str,
        approved: bool,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resumes an interrupted workflow at the human approval node with the user's decision."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        # Resume state graph execution
        state: AgentState = workflow_orchestrator.resume_workflow(
            task_id=task.id,
            approved=approved,
            feedback=feedback,
            db=db
        )

        # Synchronize execution state with DB
        OrchestrationService._sync_state_to_db(db, task, state)
        return serialize_agent_state(state)

    @staticmethod
    def cancel_orchestrated_workflow(db: Session, task_id: str) -> Dict[str, Any]:
        """Cancels an ongoing orchestrated workflow."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        workflow_orchestrator.cancel_workflow(task_id, db=db)
        task.status = TaskStatus.CANCELLED
        task.error_message = "Task cancelled by user."
        db.commit()

        return {
            "task_id": task_id,
            "status": "CANCELLED",
            "message": "Workflow successfully cancelled."
        }

    @staticmethod
    def get_workflow_state(db: Session, task_id: str) -> Dict[str, Any]:
        """Retrieves the latest state graph snapshot for a task."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        state = workflow_orchestrator.get_state(task_id, db=db)
        if state:
            return serialize_agent_state(state)

        # Fallback if no checkpoint yet
        return {
            "task_id": task.id,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "current_node": "pending",
            "messages": []
        }

    @staticmethod
    def get_checkpoints(db: Session, task_id: str) -> List[Dict[str, Any]]:
        """Lists historical checkpoint milestones for a task."""
        return checkpoint_manager.list_checkpoints(task_id, db=db)

    @staticmethod
    def _sync_state_to_db(db: Session, task: Task, state: AgentState) -> None:
        """Internal helper to reflect graph state into database models."""
        now = datetime.now(timezone.utc)

        # 1. Update Task status
        graph_status = state.get("status", "RUNNING")
        if graph_status == "WAITING_FOR_APPROVAL":
            task.status = TaskStatus.WAITING_FOR_APPROVAL
        elif graph_status == "COMPLETED":
            task.status = TaskStatus.COMPLETED
            task.completed_at = now
        elif graph_status == "CANCELLED":
            task.status = TaskStatus.CANCELLED
        elif graph_status == "FAILED":
            task.status = TaskStatus.FAILED
            task.error_message = state.get("error_message") or "Workflow failed"
        else:
            task.status = TaskStatus.RUNNING

        # 2. Update Plan
        if state.get("plan") and "execution_steps" in state["plan"]:
            task.execution_plan = state["plan"]["execution_steps"]

        # 3. Save / Update CodePatch
        if state.get("unified_diff") and state.get("file_path"):
            patch = db.query(CodePatch).filter(CodePatch.task_id == task.id).first()
            if not patch:
                patch = CodePatch(
                    task_id=task.id,
                    file_path=state["file_path"],
                    original_content=state.get("original_content", ""),
                    modified_content=state.get("modified_content", ""),
                    unified_diff=state["unified_diff"],
                    is_approved="PENDING"
                )
                db.add(patch)
            else:
                patch.file_path = state["file_path"]
                patch.modified_content = state.get("modified_content", "")
                patch.unified_diff = state["unified_diff"]
                if state.get("is_approved") is True:
                    patch.is_approved = "APPROVED"
                elif state.get("is_approved") is False:
                    patch.is_approved = "REJECTED"

        # 4. Save Test Results if not yet persisted
        for tr_data in state.get("test_results", []):
            attempt_num = tr_data.get("attempt_number", 1)
            existing = db.query(TestResult).filter(
                TestResult.task_id == task.id,
                TestResult.attempt_number == attempt_num
            ).first()
            if not existing:
                tr = TestResult(
                    task_id=task.id,
                    attempt_number=attempt_num,
                    passed=tr_data.get("passed", 0),
                    failed=tr_data.get("failed", 0),
                    errors=tr_data.get("errors", 0),
                    exit_code=tr_data.get("exit_code", 0),
                    stdout=tr_data.get("stdout", ""),
                    stderr=tr_data.get("stderr", ""),
                    failure_details=tr_data.get("failure_details", [])
                )
                db.add(tr)

        # 5. Synchronize TaskStep entries
        if state.get("messages"):
            existing_steps = db.query(TaskStep).filter(TaskStep.task_id == task.id).all()
            existing_count = len(existing_steps)
            for idx, msg in enumerate(state["messages"][existing_count:], start=existing_count + 1):
                step = TaskStep(
                    task_id=task.id,
                    step_order=idx,
                    agent_name=msg.get("role", "agent"),
                    description=msg.get("content", "")[:500],
                    status="COMPLETED" if graph_status in ["COMPLETED", "WAITING_FOR_APPROVAL"] else "RUNNING",
                    tool_calls=[],
                    output_summary=msg.get("content", "")
                )
                db.add(step)

        task.repair_attempt_count = state.get("repair_attempts", 0)
        db.commit()
        db.refresh(task)


orchestration_service = OrchestrationService()
