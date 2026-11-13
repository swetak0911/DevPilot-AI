"""
DevPilot AI - Shared Typed Agent State
Defines the canonical typed state container transferred across LangGraph nodes,
including serialization, snapshotting, and validation helpers.
"""
from typing import TypedDict, Optional, List, Dict, Any, Union
from datetime import datetime, timezone
import json
import copy


class AgentState(TypedDict, total=False):
    """
    Shared strongly-typed state dictionary that flows through every node in the LangGraph workflow.
    """
    task_id: str
    instruction: str
    task_type: str
    repo_name: str
    repo_path: str
    file_path: Optional[str]
    original_content: Optional[str]
    modified_content: Optional[str]
    unified_diff: Optional[str]
    plan: Optional[Dict[str, Any]]
    bug_report: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    test_results: List[Dict[str, Any]]
    test_passed: bool
    repair_attempts: int
    max_repair_attempts: int
    current_node: str
    status: str
    human_approval_required: bool
    is_approved: Optional[bool]
    human_feedback: Optional[str]
    error_message: Optional[str]
    messages: List[Dict[str, Any]]
    checkpoints: List[str]
    iteration_count: int
    is_cancelled: bool
    is_timed_out: bool
    started_at: str
    updated_at: str


def create_initial_state(
    task_id: str,
    instruction: str,
    repo_name: str,
    repo_path: str = ".",
    task_type: str = "BUG_FIX",
    file_path: Optional[str] = None,
    original_content: Optional[str] = None,
    max_repair_attempts: int = 3,
    human_approval_required: bool = True
) -> AgentState:
    """Creates a validated initial state for the multi-agent graph."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return AgentState(
        task_id=task_id,
        instruction=instruction,
        task_type=task_type,
        repo_name=repo_name,
        repo_path=repo_path,
        file_path=file_path,
        original_content=original_content,
        modified_content=None,
        unified_diff=None,
        plan=None,
        bug_report=None,
        validation_result=None,
        test_results=[],
        test_passed=False,
        repair_attempts=0,
        max_repair_attempts=max_repair_attempts,
        current_node="entry",
        status="RUNNING",
        human_approval_required=human_approval_required,
        is_approved=None,
        human_feedback=None,
        error_message=None,
        messages=[{
            "timestamp": now_iso,
            "role": "system",
            "node": "entry",
            "content": f"Workflow initiated for task {task_id}: '{instruction}'"
        }],
        checkpoints=[],
        iteration_count=0,
        is_cancelled=False,
        is_timed_out=False,
        started_at=now_iso,
        updated_at=now_iso
    )


def append_agent_message(
    state: AgentState,
    role: str,
    content: str,
    node: str = ""
) -> None:
    """Appends an auditable message entry to the state's message log."""
    now_iso = datetime.now(timezone.utc).isoformat()
    if "messages" not in state or state["messages"] is None:
        state["messages"] = []
    state["messages"].append({
        "timestamp": now_iso,
        "role": role,
        "node": node or state.get("current_node", ""),
        "content": content
    })
    state["updated_at"] = now_iso


def serialize_agent_state(state: AgentState) -> Dict[str, Any]:
    """Converts AgentState into a JSON-safe dictionary snapshot."""
    cloned = copy.deepcopy(dict(state))
    # Ensure all values are JSON serializable
    return json.loads(json.dumps(cloned, default=str))


def deserialize_agent_state(data: Dict[str, Any]) -> AgentState:
    """Reconstitutes AgentState from a serialized dictionary snapshot."""
    res = AgentState(**copy.deepcopy(data))
    return res
