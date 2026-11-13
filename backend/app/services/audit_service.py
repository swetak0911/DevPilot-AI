"""
DevPilot AI - Security & Compliance Audit Log Service
Records and queries security-critical actions, resource mutations,
and autonomous agent executions for compliance auditing.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating and querying audit trail logs."""

    def record_event(
        self,
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Persists a new immutable audit log event."""
        log_entry = AuditLog(
            id=str(uuid.uuid4()),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            user_id=user_id,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def list_logs(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> List[AuditLog]:
        """Queries audit log entries with optional action and resource filters."""
        query = db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)

        return query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()

    def get_audit_summary(self, db: Session) -> Dict[str, Any]:
        """Computes summary statistics across all audit log events."""
        total_events = db.query(AuditLog).count()
        recent_logs = self.list_logs(db, limit=5)
        return {
            "total_audit_events": total_events,
            "recent_actions": [
                {
                    "id": l.id,
                    "action": l.action,
                    "resource_type": l.resource_type,
                    "resource_id": l.resource_id,
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None
                }
                for l in recent_logs
            ]
        }


audit_service = AuditService()
