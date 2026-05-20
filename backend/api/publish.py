"""Phase 5-B — Publish job REST API."""
from __future__ import annotations

import logging
from typing import Any, Optional

import arq
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_PLATFORMS = ["douyin", "xiaohongshu", "tiktok"]


class PublishRequest(BaseModel):
    product_id: str
    platforms: list[str]  # ["douyin", "xiaohongshu", "tiktok"]


class PublishStatusResponse(BaseModel):
    publish_job_id: str
    product_id: str
    platform: str
    status: str
    bundle_path: Optional[str] = None
    bundle_data: Optional[dict] = None
    error_msg: Optional[str] = None
    created_at: str


@router.post("/publish/trigger")
async def trigger_publish(
    request: PublishRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger publish packaging jobs for a product across requested platforms.

    Creates a PublishJob for each platform and queues ARQ workers.
    Returns list of created job IDs.
    """
    import os

    from backend.models.publish import PublishJob
    from backend.models.trend import ContentProduct

    # Validate product exists
    result = await db.execute(
        select(ContentProduct).where(ContentProduct.id == request.product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate product is ready
    if product.status not in ("ready", "done", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Product not ready for publishing (status={product.status})",
        )

    # Validate platforms
    invalid = [p for p in request.platforms if p not in SUPPORTED_PLATFORMS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platforms: {invalid}. Supported: {SUPPORTED_PLATFORMS}",
        )

    # Create PublishJob for each platform
    created_jobs = []
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    redis = await arq.create_pool(redis_settings)

    for platform in request.platforms:
        # Check if already pending/ready for this platform
        existing_result = await db.execute(
            select(PublishJob).where(
                PublishJob.product_id == request.product_id,
                PublishJob.platform == platform,
                PublishJob.status.in_(["pending", "packaging", "ready"]),
            )
        )
        if existing_result.scalar_one_or_none():
            logger.info(f"[PublishAPI] Skipping {platform} — already has active job")
            continue

        job = PublishJob(
            product_id=request.product_id,
            platform=platform,
            status="pending",
        )
        db.add(job)
        await db.flush()  # get the ID

        # Queue ARQ worker
        await redis.enqueue_job(
            "process_publish_job",
            str(job.id),
        )
        created_jobs.append({"publish_job_id": str(job.id), "platform": platform})

    await db.commit()
    await redis.aclose()

    return {
        "product_id": request.product_id,
        "jobs_created": len(created_jobs),
        "jobs": created_jobs,
    }


@router.get("/publish/jobs/{product_id}")
async def get_publish_jobs(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PublishStatusResponse]:
    """Get all publish jobs for a product."""
    from backend.models.publish import PublishJob

    result = await db.execute(
        select(PublishJob)
        .where(PublishJob.product_id == product_id)
        .order_by(PublishJob.created_at.desc())
    )
    jobs = result.scalars().all()

    return [
        PublishStatusResponse(
            publish_job_id=str(j.id),
            product_id=str(j.product_id),
            platform=j.platform,
            status=j.status,
            bundle_path=j.bundle_path,
            bundle_data=j.bundle_data,
            error_msg=j.error_msg,
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]


@router.get("/publish/job/{job_id}")
async def get_publish_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> PublishStatusResponse:
    """Get a specific publish job by ID."""
    from backend.models.publish import PublishJob

    result = await db.execute(
        select(PublishJob).where(PublishJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Publish job not found")

    return PublishStatusResponse(
        publish_job_id=str(job.id),
        product_id=str(job.product_id),
        platform=job.platform,
        status=job.status,
        bundle_path=job.bundle_path,
        bundle_data=job.bundle_data,
        error_msg=job.error_msg,
        created_at=job.created_at.isoformat(),
    )


@router.post("/publish/job/{job_id}/mark-published")
async def mark_as_published(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Mark a ready publish job as published (user manually posted the content)."""
    from backend.models.publish import PublishJob

    result = await db.execute(
        select(PublishJob).where(PublishJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Publish job not found")

    if job.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'ready' state (current: {job.status})",
        )

    job.status = "published"
    await db.commit()
    return {"status": "published", "publish_job_id": job_id}
