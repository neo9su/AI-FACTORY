from __future__ import annotations

import logging
import os
from typing import Any, Optional

import arq
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.publish import PublishTask
from backend.models.trend import ContentProduct

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_PLATFORMS = ["douyin", "xiaohongshu", "tiktok"]

class PublishRequest(BaseModel):
    product_id: str
    platforms: list[str]

class PublishStatusResponse(BaseModel):
    publish_job_id: str
    product_id: str
    platform: str
    status: str
    bundle_path: Optional[str] = None
    bundle_data: Optional[dict] = None
    upload_result: Optional[dict] = None
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: str

def _to_status_response(task: PublishTask) -> PublishStatusResponse:
    """Helper to convert ORM model to Pydantic response."""
    package = task.publish_package or {}
    return PublishStatusResponse(
        publish_job_id=str(task.id),
        product_id=str(task.product_id),
        platform=task.platform,
        status=task.status,
        bundle_path=package.get("bundle_path"),
        bundle_data=package,
        upload_result=package.get("upload_result"),
        post_id=package.get("post_id"),
        post_url=package.get("post_url"),
        error_msg=task.error_log,
        created_at=task.created_at.isoformat(),
    )

@router.post("/publish/trigger")
async def trigger_publish(
    request: PublishRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger publish packaging jobs for a product across requested platforms."""
    result = await db.execute(
        select(ContentProduct).where(ContentProduct.id == request.product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status not in ("ready", "done", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Product not ready for publishing (status={product.status})",
        )

    invalid = [p for p in request.platforms if p not in SUPPORTED_PLATFORMS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platforms: {invalid}. Supported: {SUPPORTED_PLATFORMS}",
        )

    created_jobs = []
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    redis = await arq.create_pool(redis_settings)

    for platform in request.platforms:
        existing_result = await db.execute(
            select(PublishTask).where(
                PublishTask.product_id == request.product_id,
                PublishTask.platform == platform,
                PublishTask.status.in_(["pending", "packaging", "platform_ready"]),
            )
        )
        if existing_result.scalar_one_or_none():
            logger.info(f"[PublishAPI] Skipping {platform} — already has active job")
            continue

        task = PublishTask(
            product_id=request.product_id,
            platform=platform,
            status="pending",
        )
        db.add(task)
        await db.flush()

        await redis.enqueue_job("process_publish_job", str(task.id))
        created_jobs.append({"publish_job_id": str(task.id), "platform": platform})

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
    result = await db.execute(
        select(PublishTask)
        .where(PublishTask.product_id == product_id)
        .order_by(PublishTask.created_at.desc())
    )
    jobs = result.scalars().all()
    return [_to_status_response(j) for j in jobs]

@router.get("/publish/job/{job_id}")
async def get_publish_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> PublishStatusResponse:
    """Get a specific publish job by ID."""
    result = await db.execute(
        select(PublishTask).where(PublishTask.id == job_id)
    )
	# Wait, I need to check if the variable name is task or job. 
    # In my previous code it was task. Let's be consistent.
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Publish task not found")

    return _to_status_response(task)

@router.post("/publish/job/{job_id}/mark-published")
async def mark_as_published(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Mark a ready publish job as published (user manually posted the content)."""
    result = await db.execute(
        select(PublishTask).where(PublishTask.id == job_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Publish task not found")

    if task.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Task must be in 'ready' state (current: {task.status})",
        )

    task.status = "published"
    await db.commit()
    return {"status": "published", "publish_job_id": job_id}

@router.post("/publish/job/{job_id}/retry-upload")
async def retry_upload(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Re-queue an upload_failed job for platform upload retry."""
    import os
    from backend.models.publish import PublishTask
    
    result = await db.execute(select(PublishTask).where(PublishTask.id == job_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Publish task not found")

    if task.status not in ("upload_failed", "ready"):
        raise HTTPException(
            status_code=400,
            detail=f"Task must be in 'upload_failed' or 'ready' state (current: {task.status})",
        )

    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    redis = await arq.create_pool(redis_settings)
    task.status = "pending"
    await db.commit()
    await redis.enqueue_job("process_publish_job", str(task.id))
    await redis.aclose()

    return {"status": "pending", "publish_job_id": job_id}
