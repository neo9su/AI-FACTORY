"""
Projects API routes for CRUD operations.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.project import (
    AgentRun,
    Deployment,
    DeliveryReport,
    PermissionPolicy,
    Project,
    ProjectStatus,
    Task,
    TestRun,
)
from backend.workers.pipeline import get_arq_pool

router = APIRouter()


# Pydantic schemas
class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str
    user_requirement: str
    goal: Optional[str] = None
    tech_stack: Optional[str] = None
    template: Optional[str] = None  # e.g., "python-cli", "react-app"


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: str
    name: str
    user_requirement: str
    goal: Optional[str]
    tech_stack: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailResponse(ProjectResponse):
    """Schema for detailed project response with relationships."""

    tasks: list[dict[str, Any]] = []
    agent_runs_count: int = 0
    test_runs_count: int = 0


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """
    Create a new project.

    Args:
        project_data: Project creation data
        db: Database session

    Returns:
        Project: Created project instance
    """
    project = Project(
        id=str(uuid4()),
        name=project_data.name,
        user_requirement=project_data.user_requirement,
        goal=project_data.goal,
        tech_stack=project_data.tech_stack,
        status=ProjectStatus.CREATED,
    )

    # Apply template if specified
    if project_data.template:
        from backend.core.templates import get_template, get_template_prompt
        template = get_template(project_data.template)
        if template:
            # Use template tech_stack if not explicitly provided
            if not project.tech_stack:
                project.tech_stack = template["tech_stack"]
            # Append template guidance to requirement
            template_prompt = get_template_prompt(project_data.template)
            project.user_requirement = project.user_requirement + "\n" + template_prompt

    db.add(project)
    await db.commit()
    await db.refresh(project)

    return project


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> list[Project]:
    """
    List all projects with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by project status (e.g. "delivered", "failed")
        search: Search by project name (case-insensitive)
        db: Database session

    Returns:
        list[Project]: List of projects
    """
    query = select(Project)

    if status:
        try:
            status_enum = ProjectStatus(status)
            query = query.where(Project.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status filter

    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))

    query = query.order_by(Project.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()
    return list(projects)


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get project by ID with related data.

    Args:
        project_id: Project UUID
        db: Database session

    Returns:
        dict: Project details with tasks and counts

    Raises:
        HTTPException: If project not found
    """
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get counts
    agent_runs_result = await db.execute(
        select(AgentRun).where(AgentRun.project_id == project_id)
    )
    agent_runs_count = len(agent_runs_result.scalars().all())

    test_runs_result = await db.execute(
        select(TestRun).where(TestRun.project_id == project_id)
    )
    test_runs_count = len(test_runs_result.scalars().all())

    return {
        "id": project.id,
        "name": project.name,
        "user_requirement": project.user_requirement,
        "goal": project.goal,
        "tech_stack": project.tech_stack,
        "status": project.status.value,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority,
                "role": task.role,
            }
            for task in project.tasks
        ],
        "agent_runs_count": agent_runs_count,
        "test_runs_count": test_runs_count,
    }


@router.post("/projects/{project_id}/start")
async def start_project_pipeline(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Start the pipeline for a project.

    Args:
        project_id: Project UUID
        db: Database session

    Returns:
        dict: Job information

    Raises:
        HTTPException: If project not found
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Enqueue pipeline job
    pool = await get_arq_pool()
    job = await pool.enqueue_job("run_project_pipeline", project_id)

    return {
        "status": "queued",
        "project_id": project_id,
        "job_id": job.job_id,
    }


@router.get("/projects/{project_id}/agent-runs")
async def list_agent_runs(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List agent runs for a project.

    Args:
        project_id: Project UUID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        list[dict]: Agent run records
    """
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(AgentRun.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    agent_runs = result.scalars().all()

    return [
        {
            "id": run.id,
            "agent_name": run.agent_name,
            "status": run.status.value,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "task_id": run.task_id,
        }
        for run in agent_runs
    ]


@router.get("/projects/{project_id}/test-runs")
async def list_test_runs(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List test runs for a project.

    Args:
        project_id: Project UUID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        list[dict]: Test run records
    """
    result = await db.execute(
        select(TestRun)
        .where(TestRun.project_id == project_id)
        .order_by(TestRun.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    test_runs = result.scalars().all()

    return [
        {
            "id": run.id,
            "test_type": run.test_type,
            "command": run.command,
            "status": run.status.value,
            "error_log": run.error_log,
            "created_at": run.created_at.isoformat(),
        }
        for run in test_runs
    ]


@router.get("/projects/{project_id}/deployment")
async def get_deployment(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get latest deployment for a project.

    Args:
        project_id: Project UUID
        db: Database session

    Returns:
        dict: Deployment information

    Raises:
        HTTPException: If no deployment found
    """
    result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id)
        .order_by(Deployment.created_at.desc())
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(status_code=404, detail="No deployment found")

    return {
        "id": deployment.id,
        "environment": deployment.environment,
        "preview_url": deployment.preview_url,
        "status": deployment.status.value,
        "logs": deployment.logs,
        "created_at": deployment.created_at.isoformat(),
    }


@router.get("/projects/{project_id}/delivery-report")
async def get_delivery_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get delivery report for a project.

    Args:
        project_id: Project UUID
        db: Database session

    Returns:
        dict: Delivery report

    Raises:
        HTTPException: If no report found
    """
    result = await db.execute(
        select(DeliveryReport).where(DeliveryReport.project_id == project_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="No delivery report found")

    return {
        "id": report.id,
        "summary": report.summary,
        "passed_tests": report.passed_tests,
        "failed_tests": report.failed_tests,
        "deployment_url": report.deployment_url,
        "known_issues": report.known_issues,
        "final_status": report.final_status,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/projects/{project_id}/review")
async def get_review_report(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get the code review report for a project.

    Returns the reviewer's structured output (score, issues, suggestions).
    """
    import json

    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .where(AgentRun.agent_name == "reviewer")
        .order_by(AgentRun.started_at.desc())
    )
    review_run = result.scalar_one_or_none()

    if not review_run:
        raise HTTPException(status_code=404, detail="No review report found")

    # Parse the structured review output
    try:
        review_data = json.loads(review_run.output) if review_run.output else {}
    except (json.JSONDecodeError, TypeError):
        review_data = {"summary": review_run.output or "No review data"}

    return {
        "id": review_run.id,
        "status": review_run.status.value,
        "started_at": review_run.started_at.isoformat() if review_run.started_at else None,
        "finished_at": review_run.finished_at.isoformat() if review_run.finished_at else None,
        "review": review_data,
    }


@router.get("/templates")
async def list_templates() -> list[dict[str, Any]]:
    """
    List available project templates.

    Returns:
        list: Available templates with name, description, tech_stack
    """
    from backend.core.templates import list_templates as _list_templates
    return _list_templates()


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Soft-delete a project and clean up its workspace.

    Args:
        project_id: Project UUID
        db: Database session

    Returns:
        dict: Confirmation message
    """
    import shutil
    from pathlib import Path

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clean up workspace
    workspace = Path("./workspace") / project_id
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)

    # Delete project (cascades to tasks, agent_runs, test_runs, etc.)
    await db.delete(project)
    await db.commit()

    return {"message": f"Project '{project.name}' deleted successfully"}
