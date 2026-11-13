"""
Phase 8 Multi-Agent Orchestration (LangGraph) Test Suite
Tests Typed Agent State, StateGraph compilation, conditional routing,
checkpointing, cancellation & timeouts, and human-in-the-loop interrupts.
"""
import pytest
import os
import time

from ai_engine.orchestration.agent_state import (
    AgentState,
    create_initial_state,
    append_agent_message,
    serialize_agent_state,
    deserialize_agent_state
)
from ai_engine.orchestration.graph_engine import DevPilotStateGraph, END
from ai_engine.orchestration.checkpoint_manager import checkpoint_manager
from ai_engine.orchestration.workflow_orchestrator import workflow_orchestrator
from ai_engine.orchestration.workflow_nodes import (
    route_after_validation,
    route_after_testing,
    route_after_human_approval
)
from app.models.task import Task, TaskStatus, TaskType, TaskCheckpoint
from app.models.repository import Repository
from app.services.orchestration_service import orchestration_service


def test_agent_state_initialization_and_serialization():
    """Verifies typed state creation, message logging, and JSON serialization."""
    state = create_initial_state(
        task_id="task_state_001",
        instruction="Fix zero division in math calculation",
        repo_name="DevPilot-Core",
        task_type="BUG_FIX"
    )
    assert state["task_id"] == "task_state_001"
    assert state["status"] == "RUNNING"
    assert state["current_node"] == "entry"
    assert len(state["messages"]) == 1

    append_agent_message(state, role="test_runner", content="Sandbox test succeeded", node="testing")
    assert len(state["messages"]) == 2
    assert state["messages"][-1]["role"] == "test_runner"

    # Serialization test
    serialized = serialize_agent_state(state)
    assert isinstance(serialized, dict)
    assert serialized["task_id"] == "task_state_001"

    # Deserialization test
    restored = deserialize_agent_state(serialized)
    assert restored["task_id"] == state["task_id"]
    assert len(restored["messages"]) == 2


def test_stategraph_compilation_and_transitions():
    """Verifies building, compiling, and running a StateGraph with linear transitions."""
    graph = DevPilotStateGraph(AgentState)

    def node_a(state: AgentState) -> AgentState:
        state["current_node"] = "node_a"
        append_agent_message(state, "agent_a", "Processed step A")
        return state

    def node_b(state: AgentState) -> AgentState:
        state["current_node"] = "node_b"
        append_agent_message(state, "agent_b", "Processed step B")
        state["status"] = "COMPLETED"
        return state

    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.set_entry_point("node_a")
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", END)

    compiled = graph.compile()
    init_state = create_initial_state("task_test_graph", "Test graph", "repo")
    final_state = compiled.invoke(init_state)

    assert final_state["current_node"] == END
    assert final_state["status"] == "COMPLETED"
    assert len(final_state["messages"]) >= 3


def test_stategraph_conditional_routing():
    """Verifies dynamic edge routing based on condition functions."""
    # 1. Validation routing
    valid_state = {"validation_result": {"is_valid": True}, "repair_attempts": 0, "max_repair_attempts": 3}
    assert route_after_validation(valid_state) == "testing"

    invalid_state = {"validation_result": {"is_valid": False}, "repair_attempts": 1, "max_repair_attempts": 3}
    assert route_after_validation(invalid_state) == "coding"

    exhausted_state = {"validation_result": {"is_valid": False}, "repair_attempts": 3, "max_repair_attempts": 3}
    assert route_after_validation(exhausted_state) == "failure"

    # 2. Testing routing
    test_pass_state = {"test_passed": True, "human_approval_required": True}
    assert route_after_testing(test_pass_state) == "human_approval"

    test_pass_auto_state = {"test_passed": True, "human_approval_required": False}
    assert route_after_testing(test_pass_auto_state) == "completion"

    test_fail_state = {"test_passed": False, "repair_attempts": 1, "max_repair_attempts": 3}
    assert route_after_testing(test_fail_state) == "repair"

    # 3. Human review routing
    approved_state = {"is_approved": True}
    assert route_after_human_approval(approved_state) == "completion"

    rejected_state = {"is_approved": False}
    assert route_after_human_approval(rejected_state) == "failure"


def test_checkpoint_manager_persistence_and_restore(db_session):
    """Verifies saving, retrieving, and restoring execution state checkpoints."""
    state = create_initial_state("cp_task_01", "Inspect memory leak", "devpilot-repo")
    state["iteration_count"] = 1

    cp_id = checkpoint_manager.save_checkpoint("cp_task_01", "planning", state, db=db_session)
    assert cp_id is not None
    assert "chk_cp_task_" in cp_id

    # List checkpoints
    history = checkpoint_manager.list_checkpoints("cp_task_01", db=db_session)
    assert len(history) >= 1
    assert history[-1]["node_name"] == "planning"

    # Restore checkpoint
    restored = checkpoint_manager.restore_checkpoint("cp_task_01", cp_id, db=db_session)
    assert restored is not None
    assert restored["task_id"] == "cp_task_01"
    assert restored["instruction"] == "Inspect memory leak"


def test_workflow_cancellation():
    """Verifies that cancellation tokens halt graph execution."""
    task_id = "cancel_test_task_01"
    # Mark as cancelled before or during execution
    workflow_orchestrator.cancel_workflow(task_id)

    res = workflow_orchestrator.run_workflow(
        task_id=task_id,
        instruction="Do long work",
        repo_name="test_repo",
        repo_path="."
    )
    assert res["status"] == "CANCELLED"
    assert res["is_cancelled"] is True


def test_human_in_the_loop_approval_interrupt(db_session):
    """Verifies workflow pauses at human approval node and resumes on decision."""
    repo = Repository(
        name="hitl-repo",
        full_name="devpilot/hitl-repo",
        html_url="https://github.com/devpilot/hitl-repo",
        clone_url="https://github.com/devpilot/hitl-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    repo_ws = os.path.join(".", "execution", "workspaces", "hitl-repo")
    os.makedirs(repo_ws, exist_ok=True)
    with open(os.path.join(repo_ws, "test_health.py"), "w", encoding="utf-8") as f:
        f.write("def test_health_check(): assert True\n")

    task = Task(
        user_id="dev_user",
        repository_id=repo.id,
        title="Human review test",
        instruction="Refactor auth token expiration check",
        task_type=TaskType.BUG_FIX,
        status=TaskStatus.RUNNING,
        execution_plan=[]
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # 1. Run workflow with human approval required
    paused_state = orchestration_service.start_orchestrated_workflow(
        db=db_session,
        task_id=task.id,
        human_approval_required=True
    )
    assert paused_state["status"] == "WAITING_FOR_APPROVAL"
    assert paused_state["current_node"] == "human_approval"

    # Refresh task in db
    db_session.refresh(task)
    assert task.status == TaskStatus.WAITING_FOR_APPROVAL

    # 2. Resume workflow with approval
    completed_state = orchestration_service.resume_orchestrated_workflow(
        db=db_session,
        task_id=task.id,
        approved=True,
        feedback="Looks good to merge"
    )
    assert completed_state["status"] == "COMPLETED"
    db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED
