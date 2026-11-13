"""
Agent Service
Bridges FastAPI REST endpoints with autonomous LLM Coding Agents
and manages persistence of plans, patches, and logs in the database.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ai_engine.agents.agent_orchestrator import agent_orchestrator
from ai_engine.agents.planning_agent import planning_agent
from ai_engine.agents.bug_detection_agent import bug_detection_agent
from ai_engine.agents.coding_agent import coding_agent
from ai_engine.agents.patch_validator import patch_validator, PatchValidationResult
from app.models.task import Task, TaskStep, CodePatch, TaskStatus
from app.models.repository import Repository
from app.services.repository_service import repository_service
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Service layer for multi-agent task execution and code generation."""

    @staticmethod
    def execute_task_agents(db: Session, task: Task) -> Dict[str, Any]:
        """
        Executes the autonomous agent pipeline (Planning -> Defect Diagnosis -> Patch Generation -> Validation)
        and persists the artifacts in the database.
        """
        repo = db.query(Repository).filter(Repository.id == task.repository_id).first()
        workspace_path = repository_service.get_repository_workspace_path(repo) if repo else "."

        # Execute orchestrator pipeline
        result = agent_orchestrator.execute_task_pipeline(
            task_id=task.id,
            instruction=task.instruction,
            repository_path=workspace_path,
            task_type=task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type)
        )

        # Update Task database state
        task.execution_plan = result["plan"]["execution_steps"]
        task.active_agent = "Review Agent"
        task.status = TaskStatus.IN_REVIEW if result["status"] == "COMPLETED" else TaskStatus.RUNNING

        # Persist CodePatch record in database
        patch_info = result["patch"]
        patch = CodePatch(
            task_id=task.id,
            file_path=patch_info["file_path"],
            original_content=patch_info["original_content"],
            modified_content=patch_info["modified_content"],
            unified_diff=patch_info["unified_diff"],
            is_approved="PENDING"
        )
        db.add(patch)

        # Update/Create TaskStep records
        for i, step_data in enumerate(result["plan"]["execution_steps"], 1):
            existing_step = db.query(TaskStep).filter(
                TaskStep.task_id == task.id,
                TaskStep.step_order == i
            ).first()
            if existing_step:
                existing_step.status = "COMPLETED"
            else:
                new_step = TaskStep(
                    task_id=task.id,
                    step_order=i,
                    agent_name=step_data.get("agent", "Agent"),
                    description=step_data.get("description", ""),
                    status="COMPLETED"
                )
                db.add(new_step)

        db.commit()
        db.refresh(task)

        return result

    @staticmethod
    def validate_patch(original_content: str, unified_diff: str, file_path: str = "file.py") -> PatchValidationResult:
        """Validates patch syntax, line numbers, and dry-run application."""
        return patch_validator.validate_and_apply(original_content, unified_diff, file_path)


agent_service = AgentService()
