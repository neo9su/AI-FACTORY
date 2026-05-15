"""Tests for API endpoints."""
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.project import Project, ProjectStatus


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    """Test creating a project via API."""
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Test API Project",
            "user_requirement": "Build a test application",
            "goal": "Testing API",
            "tech_stack": "FastAPI, PostgreSQL",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test API Project"
    assert data["status"] == "created"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, db_session: AsyncSession):
    """Test listing projects via API."""
    project = Project(
        id=str(uuid4()),
        name="Test Project 1",
        user_requirement="Build app 1",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get("/api/v1/projects")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(p["name"] == "Test Project 1" for p in data)


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, db_session: AsyncSession):
    """Test getting a project by ID via API."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project.id
    assert data["name"] == "Test Project"
    assert "tasks" in data


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient):
    """Test getting a non-existent project."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/projects/{fake_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_runs(client: AsyncClient, db_session: AsyncSession):
    """Test getting agent runs for a project."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}/agent-runs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_test_runs(client: AsyncClient, db_session: AsyncSession):
    """Test getting test runs for a project."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}/test-runs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_project_missing_required_fields(client: AsyncClient):
    """Test creating a project with missing required fields."""
    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_deployment_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test getting deployment for a project without deployment."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}/deployment")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_delivery_report_not_found(
    client: AsyncClient, db_session: AsyncSession
):
    """Test getting delivery report for a project without report."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        user_requirement="Build app",
        status=ProjectStatus.CREATED,
    )
    db_session.add(project)
    await db_session.commit()

    response = await client.get(f"/api/v1/projects/{project.id}/delivery-report")

    assert response.status_code == 404
