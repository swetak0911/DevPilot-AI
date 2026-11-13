"""
DevPilot AI - Resilient StateGraph Engine (LangGraph Compatible)
Provides LangGraph state graph compilation, conditional edge routing,
execution interrupts, checkpoint callbacks, and cancellation handling.
"""
from typing import Dict, Any, Callable, Optional, List, Set, Union, Generator
import logging
import time
import copy
from datetime import datetime, timezone

from ai_engine.orchestration.agent_state import AgentState, append_agent_message

logger = logging.getLogger(__name__)

# Canonical END constant representing workflow completion
END = "__end__"


class StateGraphExecutionError(Exception):
    """Raised when an unrecoverable error occurs during state graph execution."""
    pass


class WorkflowInterrupted(Exception):
    """Raised when workflow is paused at an interrupt point (e.g. human approval)."""
    def __init__(self, node: str, state: AgentState):
        super().__init__(f"Workflow paused at interrupt point: {node}")
        self.node = node
        self.state = state


class CompiledStateGraph:
    """Compiled runnable workflow graph supporting execution, stepping, and interrupts."""

    def __init__(
        self,
        nodes: Dict[str, Callable[[AgentState], AgentState]],
        edges: Dict[str, str],
        conditional_edges: Dict[str, tuple[Callable[[AgentState], str], Optional[Dict[str, str]]]],
        entry_point: str,
        interrupt_before: Optional[List[str]] = None,
        interrupt_after: Optional[List[str]] = None,
        checkpointer: Optional[Any] = None
    ):
        self.nodes = nodes
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.entry_point = entry_point
        self.interrupt_before: Set[str] = set(interrupt_before or [])
        self.interrupt_after: Set[str] = set(interrupt_after or [])
        self.checkpointer = checkpointer

    def invoke(
        self,
        initial_state: AgentState,
        config: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """
        Executes the compiled graph starting from the entry point (or current_node)
        until END, an interrupt point, cancellation, or max iterations is reached.
        """
        config = config or {}
        max_iterations = config.get("max_iterations", 50)
        timeout_seconds = config.get("timeout_seconds", 300)
        cancellation_check = config.get("is_cancelled", lambda: False)
        start_time = time.time()

        state = copy.deepcopy(initial_state)
        current_node = state.get("current_node") or self.entry_point
        if current_node == "entry" or current_node not in self.nodes:
            current_node = self.entry_point

        step_count = state.get("iteration_count", 0)

        while current_node != END and step_count < max_iterations:
            # 1. Timeout & Cancellation checks
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                state["is_timed_out"] = True
                state["status"] = "FAILED"
                state["error_message"] = f"Workflow timed out after {elapsed:.1f} seconds"
                append_agent_message(state, "system", state["error_message"], node=current_node)
                break

            if state.get("is_cancelled", False) or cancellation_check():
                state["is_cancelled"] = True
                state["status"] = "CANCELLED"
                state["error_message"] = "Workflow was cancelled by user request"
                append_agent_message(state, "system", state["error_message"], node=current_node)
                break

            # 2. Check Interrupt Before
            if current_node in self.interrupt_before and not config.get("resume_interrupt", False):
                logger.info(f"Graph execution paused before node: {current_node}")
                state["current_node"] = current_node
                state["status"] = "WAITING_FOR_APPROVAL"
                if self.checkpointer:
                    self.checkpointer.save_checkpoint(state["task_id"], current_node, state)
                return state

            # Clear single-use resume flag after passing interrupt
            if config.get("resume_interrupt", False):
                config["resume_interrupt"] = False

            # 3. Execute current node
            node_fn = self.nodes.get(current_node)
            if not node_fn:
                raise StateGraphExecutionError(f"Node '{current_node}' not found in compiled graph.")

            step_count += 1
            state["iteration_count"] = step_count
            state["current_node"] = current_node
            state["updated_at"] = datetime.now(timezone.utc).isoformat()

            logger.info(f"[LangGraph] Executing node [{current_node}] (Step #{step_count})")
            try:
                state = node_fn(state)
            except Exception as exc:
                logger.error(f"[LangGraph] Error in node {current_node}: {exc}", exc_info=True)
                state["status"] = "FAILED"
                state["error_message"] = f"Error in node '{current_node}': {str(exc)}"
                append_agent_message(state, "system", state["error_message"], node=current_node)
                break

            # 4. Checkpoint state snapshot
            if self.checkpointer:
                self.checkpointer.save_checkpoint(state["task_id"], current_node, state)

            # Check timeout post-node execution
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                state["is_timed_out"] = True
                state["status"] = "FAILED"
                state["error_message"] = f"Workflow timed out after {elapsed:.1f} seconds"
                append_agent_message(state, "system", state["error_message"], node=current_node)
                break

            # 5. Check Interrupt After
            if current_node in self.interrupt_after:
                logger.info(f"Graph execution paused after node: {current_node}")
                state["current_node"] = current_node
                state["status"] = "WAITING_FOR_APPROVAL"
                return state

            # 6. Check node-internal interrupt signal (e.g. human_approval_node awaiting approval)
            if state.get("status") == "WAITING_FOR_APPROVAL":
                logger.info(f"Node '{current_node}' set status to WAITING_FOR_APPROVAL. Yielding.")
                return state

            # 7. Determine Next Node
            next_node = None
            if current_node in self.conditional_edges:
                route_fn, path_map = self.conditional_edges[current_node]
                decision = route_fn(state)
                if path_map and decision in path_map:
                    next_node = path_map[decision]
                else:
                    next_node = decision
            elif current_node in self.edges:
                next_node = self.edges[current_node]
            else:
                next_node = END

            logger.info(f"[LangGraph] Transition: [{current_node}] -> [{next_node}]")
            current_node = next_node

        state["current_node"] = current_node
        if step_count >= max_iterations and current_node != END:
            state["status"] = "FAILED"
            state["error_message"] = f"Exceeded maximum workflow iterations ({max_iterations})"
            append_agent_message(state, "system", state["error_message"], node=current_node)

        return state


class DevPilotStateGraph:
    """
    Standard LangGraph StateGraph builder. Provides a clean 1:1 implementation of
    LangGraph's StateGraph interface with typed state transitions and checkpoints.
    """

    def __init__(self, state_schema: type):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable[[AgentState], AgentState]] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, tuple[Callable[[AgentState], str], Optional[Dict[str, str]]]] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, key: str, action: Callable[[AgentState], AgentState]):
        """Adds a processing node to the state graph."""
        if key in self.nodes:
            raise ValueError(f"Node '{key}' already registered.")
        self.nodes[key] = action
        return self

    def set_entry_point(self, key: str):
        """Designates the starting node of the state graph."""
        if key not in self.nodes:
            raise ValueError(f"Entry point '{key}' has not been added as a node.")
        self.entry_point = key
        return self

    def add_edge(self, start_key: str, end_key: str):
        """Adds a direct deterministic edge between two nodes."""
        if start_key not in self.nodes:
            raise ValueError(f"Source node '{start_key}' is not in nodes.")
        if end_key != END and end_key not in self.nodes:
            raise ValueError(f"Target node '{end_key}' is not in nodes and is not END.")
        self.edges[start_key] = end_key
        return self

    def add_conditional_edges(
        self,
        source: str,
        path: Callable[[AgentState], str],
        path_map: Optional[Dict[str, str]] = None
    ):
        """Adds a conditional routing edge evaluated dynamically at runtime."""
        if source not in self.nodes:
            raise ValueError(f"Source node '{source}' is not in nodes.")
        self.conditional_edges[source] = (path, path_map)
        return self

    def compile(
        self,
        checkpointer: Optional[Any] = None,
        interrupt_before: Optional[List[str]] = None,
        interrupt_after: Optional[List[str]] = None
    ) -> CompiledStateGraph:
        """Compiles the StateGraph into an executable workflow graph."""
        if not self.entry_point:
            raise ValueError("StateGraph entry point has not been set.")
        return CompiledStateGraph(
            nodes=self.nodes,
            edges=self.edges,
            conditional_edges=self.conditional_edges,
            entry_point=self.entry_point,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            checkpointer=checkpointer
        )
