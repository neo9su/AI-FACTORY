"""Database models for projects, tasks, and related entities."""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


class ProjectStatus(str, enum.Enum):
    """Project status enumeration."""

    CREATED = "created"
    REQUIREMENT_ANALYZING = "requirement_analyzing"
    PLANNING = "planning"
    DEVELOPING = "developing"
    TESTING = "testing"
    FIXING = "fixing"
    REVIEWING = "reviewing"
    DEPLOYING = "deploying"
    DELIVERED = "delivered"
    FAILED = "failed"
    BLOCKED_BY_GATE = "blocked_by_gate"


class TaskStatus(str, enum.Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    RETRYING = "retrying"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class AgentStatus(str, enum.Enum):
    """Agent run status enumeration."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TestStatus(str, enum.Enum):
    """Test run status enumeration."""

    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeploymentStatus(str, enum.Enum):
    """Deployment status enumeration."""

    PENDING = "pending"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Project(Base, UUIDMixin, TimestampMixin):
    """Project model representing a software development project."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.CREATED,
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="projects")
    requirements: Mapped[Optional["Requirements"]] = relationship(
        back_populates="project",
        uselist=False,
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    test_runs: Mapped[list["TestRun"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    code_reviews: Mapped[list["CodeReview"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    deployments: Mapped[list["Deployment"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    delivery_report: Mapped[Optional["DeliveryReport"]] = relationship(
        back_populates="project",
        uselist=False,
    )
    permission_policy: Mapped[Optional["PermissionPolicy"]] = relationship(
        back_populates="project",
        uselist=False,
    )


class Requirements(Base, UUIDMixin, TimestampMixin):
    """Requirements model storing structured PRD."""

    __tablename__ = "requirements"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    prd_content: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    architecture: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    constraints: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="requirements")


class Task(Base, UUIDMixin, TimestampMixin):
    """Task model representing a development task."""

    __tablename__ = "tasks"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    dependencies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="tasks")
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    test_runs: Mapped[list["TestRun"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class AgentRun(Base, UUIDMixin, TimestampMixin):
    """Agent run model storing execution details."""

    __tablename__ = "agent_runs"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus),
        nullable=False,
        default=AgentStatus.RUNNING,
    )
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="agent_runs")
    task: Mapped[Optional["Task"]] = relationship(back_populates="agent_runs")


class TestRun(Base, UUIDMixin, TimestampMixin):
    """Test run model storing test execution results."""

    __tablename__ = "test_runs"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    test_type: Mapped[str] = mapped_column(String(100), nullable=False)
    command: Mapped[str] = mapped_column(String(500), nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus),
        nullable=False,
        default=TestStatus.RUNNING,
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="test_runs")
    task: Mapped[Optional["Task"]] = relationship(back_populates="test_runs")


class CodeReview(Base, UUIDMixin, TimestampMixin):
    """Code review model storing review results."""

    __tablename__ = "code_reviews"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(100), nullable=False)
    files_reviewed: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    issues_found: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="code_reviews")


class Deployment(Base, UUIDMixin, TimestampMixin):
    """Deployment model storing deployment information."""

    __tablename__ = "deployments"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    preview_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus),
        nullable=False,
        default=DeploymentStatus.PENDING,
    )
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="deployments")


class DeliveryReport(Base, UUIDMixin, TimestampMixin):
    """Delivery report model storing final project summary."""
    __tablename__ = "delivery_reports"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    passed_tests: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    failed_tests: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    deployment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    known_issues: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="delivery_report")
    team_projects: Mapped[list["TeamProject"]] = relationship(back_populates="project")


class PermissionPolicy(Base, UUIDMixin, TimestampMixin):
    """Permission policy model for gatekeeper."""

    __tablename__ = "permission_policies"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    allow_auto_deploy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_external_api_call: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_database_migration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_delete_operation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_production_release: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="permission_policy")
