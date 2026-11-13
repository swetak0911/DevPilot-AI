"""
DevPilot AI - Checkpoint Manager
Manages state graph execution checkpoints, enabling time-travel inspection,
workflow rollbacks, persistent storage in SQLite/PostgreSQL, and interrupt recovery.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import logging
from sqlalchemy.orm import Session

from ai_engine.orchestration.agent_state import AgentState, serialize_agent_state, deserialize_agent_state

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Stores and retrieves immutable execution state snapshots."""

    def __init__(self, db_session_factory: Optional[Any] = None):
        self._memory_store: Dict[str, List[Dict[str, Any]]] = {}
        self.db_session_factory = db_session_factory

    def save_checkpoint(
        self,
        task_id: str,
        node_name: str,
        state: AgentState,
        db: Optional[Session] = None
    ) -> str:
        """Saves a point-in-time state snapshot to memory and database."""
        step_number = state.get("iteration_count", 1)
        checkpoint_id = f"chk_{task_id[:8]}_{step_number:02d}_{node_name}"
        now_dt = datetime.now(timezone.utc)

        snapshot = serialize_agent_state(state)

        record = {
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "checkpoint_id": checkpoint_id,
            "node_name": node_name,
            "step_number": step_number,
            "state_snapshot": snapshot,
            "created_at": now_dt.isoformat()
        }

        # 1. In-memory store
        if task_id not in self._memory_store:
            self._memory_store[task_id] = []
        self._memory_store[task_id].append(record)

        # 2. Add checkpoint_id to state
        if "checkpoints" not in state or state["checkpoints"] is None:
            state["checkpoints"] = []
        if checkpoint_id not in state["checkpoints"]:
            state["checkpoints"].append(checkpoint_id)

        # 3. Database persistence if session provided
        active_db = db
        close_session = False
        if active_db is None and self.db_session_factory:
            try:
                active_db = self.db_session_factory()
                close_session = True
            except Exception:
                active_db = None

        if active_db is not None:
            try:
                from app.models.task import TaskCheckpoint
                cp_entry = TaskCheckpoint(
                    task_id=task_id,
                    checkpoint_id=checkpoint_id,
                    node_name=node_name,
                    state_snapshot=snapshot,
                    step_number=step_number,
                    created_at=now_dt
                )
                active_db.add(cp_entry)
                active_db.commit()
            except Exception as e:
                logger.warning(f"Could not persist checkpoint to database: {e}")
                if active_db:
                    active_db.rollback()
            finally:
                if close_session and active_db:
                    active_db.close()

        logger.debug(f"Saved checkpoint '{checkpoint_id}' at node '{node_name}' for task '{task_id}'.")
        return checkpoint_id

    def get_latest_checkpoint(self, task_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent checkpoint for a task."""
        # Try database first if available
        if db is not None:
            try:
                from app.models.task import TaskCheckpoint
                cp = db.query(TaskCheckpoint).filter(
                    TaskCheckpoint.task_id == task_id
                ).order_by(TaskCheckpoint.step_number.desc()).first()
                if cp:
                    return {
                        "id": cp.id,
                        "task_id": cp.task_id,
                        "checkpoint_id": cp.checkpoint_id,
                        "node_name": cp.node_name,
                        "step_number": cp.step_number,
                        "state_snapshot": cp.state_snapshot,
                        "created_at": cp.created_at.isoformat()
                    }
            except Exception as e:
                logger.warning(f"Error querying checkpoint from DB: {e}")

        # Fallback to memory store
        history = self._memory_store.get(task_id, [])
        return history[-1] if history else None

    def list_checkpoints(self, task_id: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Returns the full chronological list of checkpoints for a task."""
        if db is not None:
            try:
                from app.models.task import TaskCheckpoint
                records = db.query(TaskCheckpoint).filter(
                    TaskCheckpoint.task_id == task_id
                ).order_by(TaskCheckpoint.step_number.asc()).all()
                if records:
                    return [
                        {
                            "id": r.id,
                            "task_id": r.task_id,
                            "checkpoint_id": r.checkpoint_id,
                            "node_name": r.node_name,
                            "step_number": r.step_number,
                            "created_at": r.created_at.isoformat()
                        }
                        for r in records
                    ]
            except Exception as e:
                logger.warning(f"Error listing checkpoints from DB: {e}")

        return [
            {
                "id": r["id"],
                "task_id": r["task_id"],
                "checkpoint_id": r["checkpoint_id"],
                "node_name": r["node_name"],
                "step_number": r["step_number"],
                "created_at": r["created_at"]
            }
            for r in self._memory_store.get(task_id, [])
        ]

    def restore_checkpoint(
        self,
        task_id: str,
        checkpoint_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[AgentState]:
        """Restores an AgentState from a specific or latest checkpoint."""
        # 1. From database
        if db is not None:
            try:
                from app.models.task import TaskCheckpoint
                query = db.query(TaskCheckpoint).filter(TaskCheckpoint.task_id == task_id)
                if checkpoint_id:
                    query = query.filter(TaskCheckpoint.checkpoint_id == checkpoint_id)
                else:
                    query = query.order_by(TaskCheckpoint.step_number.desc())
                cp = query.first()
                if cp and cp.state_snapshot:
                    return deserialize_agent_state(cp.state_snapshot)
            except Exception as e:
                logger.warning(f"Error restoring checkpoint from DB: {e}")

        # 2. From in-memory store
        history = self._memory_store.get(task_id, [])
        if not history:
            return None

        if checkpoint_id:
            for item in history:
                if item["checkpoint_id"] == checkpoint_id:
                    return deserialize_agent_state(item["state_snapshot"])
            return None

        return deserialize_agent_state(history[-1]["state_snapshot"])


checkpoint_manager = CheckpointManager()
