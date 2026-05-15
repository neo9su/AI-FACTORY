"""
Tasks API routes for task management.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.project import Task

router = APIRouter()


@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List tasks for a project.

    Args:
        project_id: Project UUID
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session

    Returns:
        list[dict]: Task records
    """
    result = await db.execute(
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.priority)
        .offset(skip)
        .limit(limit)
    )
    tasks = result.scalars().all()

    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "role": task.role,
            "priority": task.priority,
            "status": task.status.value,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "dependencies": task.dependencies,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }
        for task in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get task by ID.

    Args:
        task_id: Task UUID
        db: Database session

    Returns:
        dict: Task details

    Raises:
        HTTPException: If task not found
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "role": task.role,
        "priority": task.priority,
        "status": task.status.value,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "dependencies": task.dependencies,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }
