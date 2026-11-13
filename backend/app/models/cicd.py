"""DevOps, CI/CD, Infrastructure and Risk Prediction Models."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False)
    github_run_id = Column(String(100), index=True, nullable=True)
    workflow_name = Column(String(255), nullable=False)
    event = Column(String(100), default="push", nullable=False)
    status = Column(String(50), default="completed", nullable=False)  # queued, in_progress, completed
    conclusion = Column(String(50), nullable=True)  # success, failure, cancelled
    duration_seconds = Column(Integer, default=0, nullable=False)
    commit_sha = Column(String(100), nullable=True)
    branch_name = Column(String(100), default="main", nullable=True)
    jobs_data = Column(JSON, default=list, nullable=True)
    logs_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class DeploymentPrediction(Base):
    __tablename__ = "deployment_predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False)
    commit_sha = Column(String(100), nullable=True)
    risk_score = Column(Float, nullable=False)  # 0.0 to 1.0
    risk_level = Column(String(50), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    features = Column(JSON, default=dict, nullable=False)
    contributing_factors = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
