"""Task Lifecycle and Multi-Agent Execution Models."""
from datetime import datetime, timezone
import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Enum, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskType(str, enum.Enum):
    BUG_FIX = "BUG_FIX"
    FEATURE = "FEATURE"
    REFACTOR = "REFACTOR"
    TEST_GENERATION = "TEST_GENERATION"
    CODE_REVIEW = "CODE_REVIEW"
    CICD_GENERATE = "CICD_GENERATE"
    CICD_ANALYSIS = "CICD_ANALYSIS"
    DOCKER_CONFIG = "DOCKER_CONFIG"
    K8S_CONFIG = "K8S_CONFIG"
    TERRAFORM_CONFIG = "TERRAFORM_CONFIG"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    instruction = Column(Text, nullable=False)
    task_type = Column(Enum(TaskType), default=TaskType.BUG_FIX, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True, nullable=False)
    execution_plan = Column(JSON, default=list, nullable=False)
    active_agent = Column(String(100), nullable=True)
    repair_attempt_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tasks")
    repository = relationship("Repository", back_populates="tasks")
    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan", order_by="TaskStep.step_order")
    patches = relationship("CodePatch", back_populates="task", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="task", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="task", uselist=False, cascade="all, delete-orphan")
    pull_request = relationship("PullRequest", back_populates="task", uselist=False, cascade="all, delete-orphan")
    checkpoints = relationship("TaskCheckpoint", back_populates="task", cascade="all, delete-orphan", order_by="TaskCheckpoint.step_number")


class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    step_order = Column(Integer, nullable=False)
    agent_name = Column(String(100), nullable=False)
    description = Column(String(512), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    tool_calls = Column(JSON, default=list, nullable=False)
    output_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("Task", back_populates="steps")


class CodePatch(Base):
    __tablename__ = "code_patches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    file_path = Column(String(1024), nullable=False)
    original_content = Column(Text, nullable=False)
    modified_content = Column(Text, nullable=False)
    unified_diff = Column(Text, nullable=False)
    is_approved = Column(String(20), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="patches")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)
    passed = Column(Integer, default=0, nullable=False)
    failed = Column(Integer, default=0, nullable=False)
    errors = Column(Integer, default=0, nullable=False)
    exit_code = Column(Integer, default=0, nullable=False)
    stdout = Column(Text, nullable=False)
    stderr = Column(Text, nullable=False)
    failure_details = Column(JSON, default=list, nullable=False)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="test_results")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    findings = Column(JSON, default=list, nullable=False)
    decision = Column(String(50), default="PENDING", nullable=False)  # APPROVED, REJECTED, PENDING
    score = Column(Float, default=8.5, nullable=True)
    risk_level = Column(String(50), default="LOW", nullable=True)
    reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="review")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    pr_number = Column(Integer, nullable=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    branch_name = Column(String(255), nullable=False)
    base_branch = Column(String(255), default="main", nullable=False)
    html_url = Column(String(512), nullable=True)
    status = Column(String(50), default="OPEN", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="pull_request")


class TaskCheckpoint(Base):
    __tablename__ = "task_checkpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    checkpoint_id = Column(String(100), nullable=False)
    node_name = Column(String(100), nullable=False)
    state_snapshot = Column(JSON, nullable=False)
    step_number = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="checkpoints")
