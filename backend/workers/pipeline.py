"""
ARQ worker functions for async pipeline execution.

Workers handle long-running pipeline stages asynchronously.
"""
import os
from typing import Any

from arq import create_pool
from arq.connections import RedisSettings
from dotenv import load_dotenv
from sqlalchemy import select

from backend.core.orchestrator import Orchestrator
from backend.db.session import AsyncSessionLocal
from backend.models.project import Project

load_dotenv()


async def run_project_pipeline(ctx: dict[str, Any], project_id: str) -> dict[str, str]:
    """
    ARQ worker function to run complete project pipeline.

    Args:
        ctx: ARQ context
        project_id: Project UUID

    Returns:
        dict: Result summary
    """
    async with AsyncSessionLocal() as db:
        orchestrator = Orchestrator(db)

        try:
            await orchestrator.run_pipeline(project_id)

            # Get final project status
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one()

            return {
                "status": "success",
                "project_id": project_id,
                "final_status": project.status.value,
            }

        except Exception as e:
            return {
                "status": "error",
                "project_id": project_id,
                "error": str(e),
            }


async def run_single_stage(
    ctx: dict[str, Any],
    project_id: str,
    stage: str,
) -> dict[str, str]:
    """
    ARQ worker function to run a single pipeline stage.

    Args:
        ctx: ARQ context
        project_id: Project UUID
        stage: Stage name (e.g., "planning", "testing")

    Returns:
        dict: Result summary
    """
    async with AsyncSessionLocal() as db:
        orchestrator = Orchestrator(db)

        try:
            # Load project
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one()

            # Load policy
            policy = await orchestrator._get_or_create_policy(project)

            # Execute specific stage
            if stage == "intake":
                await orchestrator._stage_intake(project)
            elif stage == "planning":
                await orchestrator._stage_planning(project)
            elif stage == "developing":
                await orchestrator._stage_developing(project, policy)
            elif stage == "testing":
                await orchestrator._stage_testing(project)
            elif stage == "fixing":
                await orchestrator._stage_fixing(project, policy)
            elif stage == "reviewing":
                await orchestrator._stage_reviewing(project)
            elif stage == "deploying":
                await orchestrator._stage_deploying(project, policy)
            elif stage == "delivered":
                await orchestrator._stage_delivered(project)
            else:
                raise ValueError(f"Unknown stage: {stage}")

            return {
                "status": "success",
                "project_id": project_id,
                "stage": stage,
            }

        except Exception as e:
            return {
                "status": "error",
                "project_id": project_id,
                "stage": stage,
                "error": str(e),
            }


class WorkerSettings:
    """ARQ worker settings."""

    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )

    functions = [
        run_project_pipeline,
        run_single_stage,
    ]

    max_jobs = 10
    job_timeout = 3600  # 1 hour
    keep_result = 3600  # Keep results for 1 hour


async def get_arq_pool():
    """Get ARQ redis pool for enqueueing jobs."""
    return await create_pool(WorkerSettings.redis_settings)
