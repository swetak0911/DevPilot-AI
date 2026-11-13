"""
DevPilot AI - Phase 8 Verification Suite
Tests Multi-Agent Orchestration (LangGraph): Typed Agent State, StateGraph Engine,
Conditional Edge Routing, Checkpointing, Cancellation & Timeouts, Human-in-the-Loop Interrupts,
and REST APIs (/orchestrate, /resume, /cancel, /workflow-state, /checkpoints).
Run directly using: python verify_phase8.py
"""
import sys
import os
import tempfile
import time

# Add root directory and backend directory to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def run_phase8_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 8 Multi-Agent Orchestration (LangGraph) Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
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
    from app.models.repository import Repository
    from app.models.task import Task, TaskStep, CodePatch, TestResult, TaskCheckpoint, TaskType, TaskStatus
    from app.services.orchestration_service import orchestration_service

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Shared Typed Agent State & Serialization Integrity
        try:
            state = create_initial_state(
                task_id="p8_task_01",
                instruction="Fix authentication token validation",
                repo_name="devpilot-core",
                task_type="BUG_FIX"
            )
            assert state["task_id"] == "p8_task_01"
            assert state["status"] == "RUNNING"
            assert state["current_node"] == "entry"
            assert len(state["messages"]) == 1

            append_agent_message(state, role="planning_agent", content="Decomposed into 4 steps", node="planning")
            assert len(state["messages"]) == 2

            serialized = serialize_agent_state(state)
            assert isinstance(serialized, dict)
            assert serialized["task_id"] == "p8_task_01"

            restored = deserialize_agent_state(serialized)
            assert restored["task_id"] == state["task_id"]
            assert len(restored["messages"]) == 2
            print(f" [PASS] 1. Shared Typed Agent State & Serialization Integrity: OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Shared Typed Agent State: {e}")

        # Check 2: StateGraph Engine Compilation & Step Transitions
        try:
            test_graph = DevPilotStateGraph(AgentState)

            def step_one(s: AgentState) -> AgentState:
                s["current_node"] = "step_one"
                append_agent_message(s, "agent_1", "Finished step 1")
                return s

            def step_two(s: AgentState) -> AgentState:
                s["current_node"] = "step_two"
                append_agent_message(s, "agent_2", "Finished step 2")
                s["status"] = "COMPLETED"
                return s

            test_graph.add_node("step_one", step_one)
            test_graph.add_node("step_two", step_two)
            test_graph.set_entry_point("step_one")
            test_graph.add_edge("step_one", "step_two")
            test_graph.add_edge("step_two", END)

            compiled = test_graph.compile()
            init_s = create_initial_state("g_task", "Run transitions", "repo")
            final_s = compiled.invoke(init_s)

            assert final_s["current_node"] == END
            assert final_s["status"] == "COMPLETED"
            assert final_s["iteration_count"] == 2
            print(f" [PASS] 2. StateGraph Compilation & Step Transitions: OK (2 nodes visited, status COMPLETED)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. StateGraph Compilation & Step Transitions: {e}")

        # Check 3: Dynamic Conditional Edge Routing
        try:
            # 1. Validation routing
            assert route_after_validation({"validation_result": {"is_valid": True}}) == "testing"
            assert route_after_validation({"validation_result": {"is_valid": False}, "repair_attempts": 0, "max_repair_attempts": 3}) == "coding"
            assert route_after_validation({"validation_result": {"is_valid": False}, "repair_attempts": 3, "max_repair_attempts": 3}) == "failure"

            # 2. Testing routing
            assert route_after_testing({"test_passed": True, "human_approval_required": True}) == "human_approval"
            assert route_after_testing({"test_passed": True, "human_approval_required": False}) == "completion"
            assert route_after_testing({"test_passed": False, "repair_attempts": 1, "max_repair_attempts": 3}) == "repair"
            assert route_after_testing({"test_passed": False, "repair_attempts": 3, "max_repair_attempts": 3}) == "failure"

            # 3. Human approval routing
            assert route_after_human_approval({"is_approved": True}) == "completion"
            assert route_after_human_approval({"is_approved": False}) == "failure"
            assert route_after_human_approval({"is_approved": None}) == END
            print(f" [PASS] 3. Dynamic Conditional Edge Routing (Validation/Testing/HITL Branching): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. Dynamic Conditional Edge Routing: {e}")

        # Check 4: Checkpointing & State Snapshot Persistence
        try:
            chk_state = create_initial_state("chk_verify_task", "Verify checkpointing", "test_repo")
            chk_state["iteration_count"] = 1
            cp_id = checkpoint_manager.save_checkpoint("chk_verify_task", "planning", chk_state, db=db)
            assert cp_id is not None
            assert "chk_chk_veri" in cp_id

            # Verify retrieval
            cp_list = checkpoint_manager.list_checkpoints("chk_verify_task", db=db)
            assert len(cp_list) >= 1
            assert cp_list[-1]["node_name"] == "planning"

            restored_state = checkpoint_manager.restore_checkpoint("chk_verify_task", cp_id, db=db)
            assert restored_state is not None
            assert restored_state["task_id"] == "chk_verify_task"
            assert restored_state["instruction"] == "Verify checkpointing"
            print(f" [PASS] 4. Checkpointing & State Persistence (Checkpoint: {cp_id}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Checkpointing & State Persistence: {e}")

        # Check 5: Workflow Cancellation & Execution Timeout Guards
        try:
            cancel_task_id = "test_cancel_flow_99"
            workflow_orchestrator.cancel_workflow(cancel_task_id)

            cancelled_res = workflow_orchestrator.run_workflow(
                task_id=cancel_task_id,
                instruction="Workflow should halt on cancel",
                repo_name="devpilot_repo"
            )
            assert cancelled_res["status"] == "CANCELLED"
            assert cancelled_res["is_cancelled"] is True

            # Test timeout guard
            slow_graph = DevPilotStateGraph(AgentState)
            def slow_node(s: AgentState) -> AgentState:
                time.sleep(0.3)
                return s
            slow_graph.add_node("slow", slow_node)
            slow_graph.set_entry_point("slow")
            slow_graph.add_edge("slow", END)
            compiled_slow = slow_graph.compile()
            slow_state = create_initial_state("timeout_task", "Test timeout", "repo")
            timeout_res = compiled_slow.invoke(slow_state, config={"timeout_seconds": 0.1})
            assert timeout_res["is_timed_out"] is True
            assert timeout_res["status"] == "FAILED"
            print(f" [PASS] 5. Workflow Cancellation & Execution Timeout Guards: OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Workflow Cancellation & Timeout Guards: {e}")

        # Check 6: Human-in-the-Loop Interrupt & Approval Resumption
        try:
            test_repo = db.query(Repository).filter(Repository.name == "orchestration-repo").first()
            if not test_repo:
                test_repo = Repository(
                    name="orchestration-repo",
                    full_name="devpilot/orchestration-repo",
                    html_url="https://github.com/devpilot/orchestration-repo",
                    clone_url="https://github.com/devpilot/orchestration-repo.git",
                    default_branch="main"
                )
                db.add(test_repo)
                db.commit()
                db.refresh(test_repo)

            repo_ws = os.path.join(".", "execution", "workspaces", "orchestration-repo")
            os.makedirs(repo_ws, exist_ok=True)
            with open(os.path.join(repo_ws, "test_health.py"), "w", encoding="utf-8") as f:
                f.write("def test_health_check(): assert True\n")

            hitl_task = Task(
                user_id="lead_developer",
                repository_id=test_repo.id,
                title="Orchestrated bug fix with human gate",
                instruction="Fix security token validation and pass tests",
                task_type=TaskType.BUG_FIX,
                status=TaskStatus.RUNNING,
                execution_plan=[]
            )
            db.add(hitl_task)
            db.commit()
            db.refresh(hitl_task)

            # Start workflow with human approval required
            paused_flow = orchestration_service.start_orchestrated_workflow(
                db=db,
                task_id=hitl_task.id,
                human_approval_required=True
            )
            assert paused_flow["status"] == "WAITING_FOR_APPROVAL"
            assert paused_flow["current_node"] == "human_approval"

            db.refresh(hitl_task)
            assert hitl_task.status == TaskStatus.WAITING_FOR_APPROVAL

            # Resume workflow with approval
            resumed_flow = orchestration_service.resume_orchestrated_workflow(
                db=db,
                task_id=hitl_task.id,
                approved=True,
                feedback="Approved by security team"
            )
            assert resumed_flow["status"] == "COMPLETED"
            db.refresh(hitl_task)
            assert hitl_task.status == TaskStatus.COMPLETED
            print(f" [PASS] 6. Human-in-the-Loop Interrupt & Approval Resumption: OK (Paused at review, Resumed to COMPLETED)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Human-in-the-Loop Interrupt & Resumption: {e}")

        # Check 7: Multi-Agent Orchestration REST APIs (/orchestrate, /resume, /cancel, /workflow-state, /checkpoints)
        try:
            api_task = Task(
                user_id="api_tester",
                repository_id=test_repo.id,
                title="API Orchestrated Execution Test",
                instruction="Fix memory leak in buffer pool",
                task_type=TaskType.BUG_FIX,
                status=TaskStatus.PENDING,
                execution_plan=[]
            )
            db.add(api_task)
            db.commit()
            db.refresh(api_task)

            # 1. Trigger Orchestrate API
            orch_resp = client.post(
                f"/api/tasks/{api_task.id}/orchestrate",
                json={"human_approval_required": True, "max_repair_attempts": 3}
            )
            assert orch_resp.status_code == 200, f"Orchestrate API failed: {orch_resp.text}"
            orch_data = orch_resp.json()
            assert orch_data["status"] in ["WAITING_FOR_APPROVAL", "COMPLETED"]

            # 2. Get Workflow State API
            state_resp = client.get(f"/api/tasks/{api_task.id}/workflow-state")
            assert state_resp.status_code == 200
            assert state_resp.json()["task_id"] == api_task.id

            # 3. Get Checkpoints API
            cp_resp = client.get(f"/api/tasks/{api_task.id}/checkpoints")
            assert cp_resp.status_code == 200
            assert len(cp_resp.json()["checkpoints"]) >= 1

            # 4. Resume API
            resume_resp = client.post(
                f"/api/tasks/{api_task.id}/resume",
                json={"approved": True, "feedback": "API test approval confirmed"}
            )
            assert resume_resp.status_code == 200
            assert resume_resp.json()["status"] == "COMPLETED"

            # 5. Cancel API
            cancel_resp = client.post(f"/api/tasks/{api_task.id}/cancel")
            assert cancel_resp.status_code == 200
            assert cancel_resp.json()["status"] == "CANCELLED"

            print(f" [PASS] 7. Multi-Agent Orchestration REST APIs (/orchestrate, /resume, /cancel, /workflow-state, /checkpoints): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. Multi-Agent Orchestration REST APIs: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 8 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks


if __name__ == "__main__":
    success = run_phase8_verification()
    sys.exit(0 if success else 1)
