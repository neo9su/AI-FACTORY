"""
Product Deployment API — 网站部署 / 自动发布
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import arq
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.trend import ContentProduct

logger = logging.getLogger(__name__)
router = APIRouter()


class ServerInfo(BaseModel):
    host: str
    port: int = 22
    username: str = "root"
    password: str
    web_root: str = "/var/www/html"


class DeployRequest(BaseModel):
    product_id: str
    server: ServerInfo


@router.post("/deploy/product")
async def deploy_product(
    request: DeployRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """将产品部署到用户指定的服务器"""
    # 验证产品存在且 ready
    result = await db.execute(
        select(ContentProduct).where(ContentProduct.id == request.product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Product not ready for deploy (status={product.status})",
        )

    # 入队部署任务
    from backend.workers.pipeline import WorkerSettings

    redis = await arq.create_pool(WorkerSettings.redis_settings)
    job = await redis.enqueue_job(
        "deploy_product_to_server",
        product_id=request.product_id,
        server=request.server.model_dump(),
    )
    await redis.aclose()

    return {
        "status": "deploying",
        "product_id": request.product_id,
        "job_id": job.job_id if job else None,
        "message": f"部署任务已提交到 {request.server.host}:{request.server.port}，将在后台执行",
    }


@router.get("/deploy/status/{product_id}")
async def get_deploy_status(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询产品的部署状态"""
    from backend.models.publish import PublishTask

    result = await db.execute(
        select(PublishTask)
        .where(
            PublishTask.product_id == product_id,
            PublishTask.platform == "website",
        )
        .order_by(PublishTask.created_at.desc())
        .limit(1)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"product_id": product_id, "status": "not_deployed"}

    package = task.publish_package or {}
    return {
        "product_id": product_id,
        "status": task.status,
        "deploy_url": package.get("deploy_url"),
        "error_msg": task.error_log,
        "created_at": task.created_at.isoformat(),
    }
