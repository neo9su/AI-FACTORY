"""Tests for database models."""
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.project import (
    AgentRun,
    AgentStatus,
    CodeReview,
    Deployment,
    DeploymentStatus,
    DeliveryReport,
    PermissionPolicy,
    Project,
    ProjectStatus,
    Requirements,
    Task,
    TaskStatus,
    TestRun,
    TestStatus,
)


@pytest.mark.asyncio
async def test_create_project(db_session: AsyncSession):
    """Test creating a project."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        goal="Testing",
        tech_stack="Python, FastAPI",
        status=ProjectStatus.CREATED,
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    assert project.id is not None
    assert project.name == "Test Project"
    assert project.status == ProjectStatus.CREATED


@pytest.mark.asyncio
async def test_create_requirements(db_session: AsyncSession):
    """Test creating requirements."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    requirements = Requirements(
        id=str(uuid4()),
        project_id=project.id,
        prd_content="Detailed PRD content here",
        features={"auth": True, "api": True},
        architecture={"frontend": "React", "backend": "FastAPI"},
    )

    db_session.add(requirements)
    await db_session.commit()
    await db_session.refresh(requirements)

    assert requirements.project_id == project.id
    assert requirements.features["auth"] is True


@pytest.mark.asyncio
async def test_create_task(db_session: AsyncSession):
    """Test creating a task."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    task = Task(
        id=str(uuid4()),
        project_id=project.id,
        title="Implement authentication",
        description="Add user authentication with JWT",
        role="backend_developer",
        priority=1,
        status=TaskStatus.PENDING,
    )

    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    assert task.project_id == project.id
    assert task.title == "Implement authentication"
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_create_agent_run(db_session: AsyncSession):
    """Test creating an agent run."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    from datetime import datetime

    agent_run = AgentRun(
        id=str(uuid4()),
        project_id=project.id,
        agent_name="planner",
        input="Create project plan",
        output="Plan created successfully",
        logs="Agent execution logs",
        status=AgentStatus.SUCCESS,
        started_at=datetime.utcnow(),
    )

    db_session.add(agent_run)
    await db_session.commit()
    await db_session.refresh(agent_run)

    assert agent_run.project_id == project.id
    assert agent_run.agent_name == "planner"
    assert agent_run.status == AgentStatus.SUCCESS


@pytest.mark.asyncio
async def test_create_test_run(db_session: AsyncSession):
    """Test creating a test run."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    test_run = TestRun(
        id=str(uuid4()),
        project_id=project.id,
        test_type="unit",
        command="pytest tests/",
        result="All tests passed",
        status=TestStatus.PASSED,
    )

    db_session.add(test_run)
    await db_session.commit()
    await db_session.refresh(test_run)

    assert test_run.project_id == project.id
    assert test_run.test_type == "unit"
    assert test_run.status == TestStatus.PASSED


@pytest.mark.asyncio
async def test_create_deployment(db_session: AsyncSession):
    """Test creating a deployment."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    deployment = Deployment(
        id=str(uuid4()),
        project_id=project.id,
        environment="preview",
        preview_url="https://preview.example.com",
        status=DeploymentStatus.SUCCESS,
    )

    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    assert deployment.project_id == project.id
    assert deployment.environment == "preview"
    assert deployment.status == DeploymentStatus.SUCCESS


@pytest.mark.asyncio
async def test_create_permission_policy(db_session: AsyncSession):
    """Test creating a permission policy."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    policy = PermissionPolicy(
        id=str(uuid4()),
        project_id=project.id,
        allow_auto_deploy=True,
        allow_production_release=False,
        max_retry_count=5,
    )

    db_session.add(policy)
    await db_session.commit()
    await db_session.refresh(policy)

    assert policy.project_id == project.id
    assert policy.allow_auto_deploy is True
    assert policy.max_retry_count == 5


@pytest.mark.asyncio
async def test_project_relationships(db_session: AsyncSession):
    """Test project relationships."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build a test app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    task = Task(
        id=str(uuid4()),
        project_id=project.id,
        title="Test Task",
        description="Testing",
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.commit()

    result = await db_session.execute(
        select(Project).where(Project.id == project.id)
    )
    loaded_project = result.scalar_one()

    assert loaded_project.id == project.id
    assert loaded_project.name == "Test Project"
