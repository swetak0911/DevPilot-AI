"""
DevPilot AI - Workflow Orchestrator (LangGraph Multi-Agent Pipeline)
Builds, compiles, and manages the lifecycle of multi-agent state graphs,
handling interrupts, human approvals, timeouts, cancellations, and checkpointing.
"""
from typing import Dict, Any, Optional, Set
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ai_engine.orchestration.agent_state import (
    AgentState,
    create_initial_state,
    append_agent_message,
    serialize_agent_state
)
from ai_engine.orchestration.graph_engine import DevPilotStateGraph, CompiledStateGraph, END
from ai_engine.orchestration.checkpoint_manager import checkpoint_manager
from ai_engine.orchestration.workflow_nodes import (
    planning_node,
    bug_detection_node,
    coding_node,
    validation_node,
    testing_node,
    repair_evaluation_node,
    human_approval_node,
    completion_node,
    failure_node,
    route_after_validation,
    route_after_testing,
    route_after_repair,
    route_after_human_approval
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Manages the lifecycle of multi-agent coding workflows via LangGraph state graphs."""

    def __init__(self):
        self._cancellation_tokens: Set[str] = set()
        self._compiled_graph: Optional[CompiledStateGraph] = None
        self._initialize_graph()

    def _initialize_graph(self):
        """Constructs and compiles the master state graph."""
        builder = DevPilotStateGraph(AgentState)

        # 1. Register Nodes
        builder.add_node("planning", planning_node)
        builder.add_node("bug_detection", bug_detection_node)
        builder.add_node("coding", coding_node)
        builder.add_node("validation", validation_node)
        builder.add_node("testing", testing_node)
        builder.add_node("repair", repair_evaluation_node)
        builder.add_node("human_approval", human_approval_node)
        builder.add_node("completion", completion_node)
        builder.add_node("failure", failure_node)

        # 2. Set Entry Point
        builder.set_entry_point("planning")

        # 3. Add Deterministic Edges
        builder.add_edge("planning", "bug_detection")
        builder.add_edge("bug_detection", "coding")
        builder.add_edge("coding", "validation")
        builder.add_edge("repair", "coding")
        builder.add_edge("completion", END)
        builder.add_edge("failure", END)

        # 4. Add Conditional Edges
        builder.add_conditional_edges(
            source="validation",
            path=route_after_validation,
            path_map={"testing": "testing", "coding": "coding", "failure": "failure"}
        )
        builder.add_conditional_edges(
            source="testing",
            path=route_after_testing,
            path_map={
                "human_approval": "human_approval",
                "completion": "completion",
                "repair": "repair",
                "failure": "failure"
            }
        )
        builder.add_conditional_edges(
            source="human_approval",
            path=route_after_human_approval,
            path_map={"completion": "completion", "failure": "failure", "__end__": END}
        )

        # 5. Compile Graph with Checkpointing
        self._compiled_graph = builder.compile(
            checkpointer=checkpoint_manager
        )
        logger.info("DevPilot Multi-Agent StateGraph compiled successfully.")

    def run_workflow(
        self,
        task_id: str,
        instruction: str,
        repo_name: str,
        repo_path: str = ".",
        task_type: str = "BUG_FIX",
        file_path: Optional[str] = None,
        original_content: Optional[str] = None,
        max_repair_attempts: int = 3,
        human_approval_required: bool = True,
        timeout_seconds: int = 300
    ) -> AgentState:
        """
        Executes a new autonomous coding workflow from entry to completion or interrupt.
        """
        initial_state = create_initial_state(
            task_id=task_id,
            instruction=instruction,
            repo_name=repo_name,
            repo_path=repo_path,
            task_type=task_type,
            file_path=file_path,
            original_content=original_content,
            max_repair_attempts=max_repair_attempts,
            human_approval_required=human_approval_required
        )

        if task_id in self._cancellation_tokens:
            initial_state["is_cancelled"] = True
            initial_state["status"] = "CANCELLED"
            initial_state["error_message"] = "Workflow was cancelled by user request."
            append_agent_message(initial_state, "system", "Workflow was cancelled by user request.", node="cancelled")
            checkpoint_manager.save_checkpoint(task_id, "cancelled", initial_state)
            return initial_state

        # Save initial checkpoint
        checkpoint_manager.save_checkpoint(task_id, "entry", initial_state)

        config = {
            "max_iterations": 30,
            "timeout_seconds": timeout_seconds,
            "is_cancelled": lambda: task_id in self._cancellation_tokens
        }

        final_state = self._compiled_graph.invoke(initial_state, config=config)
        return final_state

    def resume_workflow(
        self,
        task_id: str,
        approved: bool,
        feedback: Optional[str] = None,
        db: Optional[Session] = None,
        timeout_seconds: int = 300
    ) -> AgentState:
        """
        Resumes an interrupted workflow at the human_approval node with the user's decision.
        """
        # Restore latest checkpoint
        current_state = checkpoint_manager.restore_checkpoint(task_id=task_id, db=db)
        if not current_state:
            raise ValueError(f"No checkpoint found to resume for task '{task_id}'.")

        # Update approval decision in state
        current_state["is_approved"] = approved
        current_state["human_feedback"] = feedback or ("Approved by user" if approved else "Rejected by user")
        current_state["current_node"] = "human_approval"
        current_state["status"] = "RUNNING"

        append_agent_message(
            current_state,
            role="human",
            content=f"Human review submitted: {'APPROVED' if approved else 'REJECTED'}. Feedback: {current_state['human_feedback']}",
            node="human_approval"
        )

        config = {
            "max_iterations": 20,
            "timeout_seconds": timeout_seconds,
            "resume_interrupt": True,
            "is_cancelled": lambda: task_id in self._cancellation_tokens
        }

        # Invoke from current node with human approval answered
        final_state = self._compiled_graph.invoke(current_state, config=config)
        return final_state

    def cancel_workflow(self, task_id: str, db: Optional[Session] = None) -> bool:
        """Signals active cancellation for the given task workflow."""
        self._cancellation_tokens.add(task_id)

        # If we have a checkpoint, mark state as cancelled immediately
        current_state = checkpoint_manager.restore_checkpoint(task_id=task_id, db=db)
        if current_state:
            current_state["is_cancelled"] = True
            current_state["status"] = "CANCELLED"
            current_state["error_message"] = "Workflow cancelled by user."
            append_agent_message(current_state, "system", "Workflow explicitly cancelled by user.", node="cancelled")
            checkpoint_manager.save_checkpoint(task_id, "cancelled", current_state, db=db)
            return True
        return True

    def get_state(self, task_id: str, db: Optional[Session] = None) -> Optional[AgentState]:
        """Retrieves the latest state of a task from its latest checkpoint."""
        return checkpoint_manager.restore_checkpoint(task_id=task_id, db=db)


workflow_orchestrator = WorkflowOrchestrator()
