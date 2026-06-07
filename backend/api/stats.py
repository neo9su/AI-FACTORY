"""
Dashboard statistics API.

Provides aggregated metrics for the factory dashboard:
- Total projects, success rate, average pipeline duration
- Token usage summary across all agent runs
- Status distribution breakdown
"""
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.project import (
    AgentRun,
    AgentStatus,
    Project,
    ProjectStatus,
    Task,
    TestRun,
)

router = APIRouter()


@router.get("/stats/overview")
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get factory-wide overview statistics.

    Returns:
        dict: Aggregated factory metrics including project counts,
              success rates, performance stats, and token usage.
    """
    # Total projects
    total_result = await db.execute(select(func.count(Project.id)))
    total_projects = total_result.scalar() or 0

    # Status distribution
    status_result = await db.execute(
        select(Project.status, func.count(Project.id)).group_by(Project.status)
    )
    status_distribution = {
        row[0].value if hasattr(row[0], "value") else str(row[0]): row[1]
        for row in status_result.all()
    }

    # Success rate
    delivered = status_distribution.get("delivered", 0)
    failed = status_distribution.get("failed", 0)
    completed_total = delivered + failed
    success_rate = (delivered / completed_total * 100) if completed_total > 0 else 0.0

    # Average pipeline duration (for delivered projects)
    duration_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Project.updated_at) - func.extract("epoch", Project.created_at)
            )
        ).where(Project.status == ProjectStatus.DELIVERED)
    )
    avg_duration_seconds = duration_result.scalar() or 0

    # Token usage from agent run logs (parse the log format)
    agent_runs_result = await db.execute(
        select(AgentRun.logs).where(AgentRun.logs.ilike("%tokens=%"))
    )
    total_tokens = 0
    total_llm_calls = 0
    for row in agent_runs_result.all():
        log = row[0] or ""
        if "tokens=" in log:
            total_llm_calls += 1
            try:
                token_part = log.split("tokens=")[1].split(" ")[0]
                total_tokens += int(token_part)
            except (IndexError, ValueError):
                pass

    # Recent activity (last 24h)
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent_result = await db.execute(
        select(func.count(Project.id)).where(Project.created_at >= yesterday)
    )
    projects_last_24h = recent_result.scalar() or 0

    # Total tasks and test runs
    tasks_result = await db.execute(select(func.count(Task.id)))
    total_tasks = tasks_result.scalar() or 0

    test_runs_result = await db.execute(select(func.count(TestRun.id)))
    total_test_runs = test_runs_result.scalar() or 0

    return {
        "total_projects": total_projects,
        "success_rate": round(success_rate, 1),
        "avg_duration_seconds": round(avg_duration_seconds, 1),
        "status_distribution": status_distribution,
        "token_usage": {
            "total_tokens": total_tokens,
            "total_llm_calls": total_llm_calls,
            "avg_tokens_per_call": round(total_tokens / total_llm_calls, 0) if total_llm_calls else 0,
        },
        "recent": {
            "projects_last_24h": projects_last_24h,
            "total_tasks": total_tasks,
            "total_test_runs": total_test_runs,
        },
    }


@router.get("/stats/timeline")
async def get_timeline_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get daily project creation timeline.

    Args:
        days: Number of days to look back (default: 7)
        db: Database session

    Returns:
        list: Daily project counts for the timeline chart.
    """
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Project.created_at).label("date"),
            func.count(Project.id).label("count"),
        )
        .where(Project.created_at >= since)
        .group_by(func.date(Project.created_at))
        .order_by(func.date(Project.created_at))
    )

    timeline = [
        {"date": str(row.date), "count": row.count}
        for row in result.all()
    ]

    return timeline


@router.get("/stats/stages")
async def get_stage_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get per-stage pipeline statistics.

    Returns:
        dict: Stage-by-stage execution stats including counts,
              average durations, and failure rates.
    """
    # Get all AgentRuns grouped by agent_name (= stage)
    from sqlalchemy import case

    result = await db.execute(
        select(
            AgentRun.agent_name,
            func.count(AgentRun.id),
            func.sum(
                func.extract("epoch", AgentRun.finished_at) -
                func.extract("epoch", AgentRun.started_at)
            ),
            func.sum(case((AgentRun.status == AgentStatus.SUCCESS, 1), else_=0)),
            func.sum(case((AgentRun.status == AgentStatus.FAILED, 1), else_=0)),
        ).group_by(AgentRun.agent_name)
    )

    stages = []
    for row in result.all():
        name, count, total_duration, success_count, fail_count = row
        stages.append({
            "name": name,
            "executions": count,
            "avg_duration_seconds": round(total_duration / count, 1) if total_duration and count else 0,
            "success_count": success_count or 0,
            "fail_count": fail_count or 0,
            "failure_rate": round((fail_count or 0) / count * 100, 1) if count > 0 else 0,
        })

    return {"stages": stages}


@router.get("/stats/errors")
async def get_error_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get error distribution across pipeline stages.

    Returns:
        dict: Error counts grouped by stage.
    """
    result = await db.execute(
        select(AgentRun.logs).where(
            AgentRun.status == AgentStatus.FAILED,
            AgentRun.logs.isnot(None),
        )
    )

    error_by_stage: dict[str, int] = {}
    for row in result.all():
        log = row[0] or ""
        if "Error:" in log:
            stage = "unknown"
            error_by_stage[stage] = error_by_stage.get(stage, 0) + 1

    failed_projects = await db.execute(
        select(func.count(Project.id))
        .where(Project.status == ProjectStatus.FAILED)
    )
    total_failures = failed_projects.scalar() or 0

    return {
        "total_failed_projects": total_failures,
        "errors_by_stage": error_by_stage,
    }


@router.get("/stats/history")
async def get_pipeline_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get recent pipeline run history.

    Args:
        limit: Number of recent projects to return (default: 20)

    Returns:
        list: Recent pipeline runs with metadata.
    """
    agent_count_subq = (
        select(func.count(AgentRun.id))
        .where(AgentRun.project_id == Project.id)
        .scalar_subquery()
    )
    task_count_subq = (
        select(func.count(Task.id))
        .where(Task.project_id == Project.id)
        .scalar_subquery()
    )

    result = await db.execute(
        select(
            Project.id,
            Project.name,
            Project.status,
            Project.created_at,
            Project.updated_at,
            func.extract("epoch", Project.updated_at) -
            func.extract("epoch", Project.created_at),
            agent_count_subq,
            task_count_subq,
        )
        .order_by(Project.created_at.desc())
        .limit(limit)
    )

    history = []
    for row in result.all():
        project_id, name, status, created_at, updated_at, duration, agent_runs, tasks = row
        history.append({
            "id": project_id,
            "name": name,
            "status": status.value if hasattr(status, "value") else str(status),
            "created_at": created_at.isoformat() if created_at else "",
            "duration_seconds": round(duration, 1) if duration else 0,
            "agent_runs": agent_runs or 0,
            "tasks": tasks or 0,
        })

    return history
