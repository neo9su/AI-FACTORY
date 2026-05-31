"""Opportunities API — 商机报告管理"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import arq
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.trend import ContentProduct, OpportunityReport

router = APIRouter()


class OpportunityResponse(BaseModel):
    id: str
    topic: str
    why_viral: str
    core_emotions: list
    core_pain_points: list
    willingness_to_pay: str
    product_suggestions: list
    best_product: Optional[str]
    roi_score: float
    automation_score: float
    seo_value: Optional[str]
    lifecycle: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class GenerateProductRequest(BaseModel):
    product_type: str  # ebook / personality_test / short_video / comic_drama


class ProductResponse(BaseModel):
    id: str
    opportunity_id: str
    product_type: str
    title: Optional[str]
    status: str
    content_url: Optional[str]
    meta: Optional[dict]
    tts_status: Optional[str]
    tts_audio_urls: Optional[list]
    tts_error: Optional[str]
    cover_image_url: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/opportunities", response_model=list[OpportunityResponse])
async def list_opportunities(
    min_roi: float = 0.0,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """获取商机报告列表（按ROI排序）"""
    query = (
        select(OpportunityReport)
        .where(OpportunityReport.roi_score >= min_roi)
        .order_by(desc(OpportunityReport.roi_score))
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str,
    session: AsyncSession = Depends(get_db),
):
    """获取商机报告详情"""
    result = await session.execute(
        select(OpportunityReport).where(OpportunityReport.id == opportunity_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Opportunity report not found")
    return report


@router.post("/opportunities/{opportunity_id}/generate-product")
async def generate_product(
    opportunity_id: str,
    request: GenerateProductRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue content product generation via ARQ worker"""
    from backend.workers.pipeline import WorkerSettings

    # 获取商机报告
    result = await session.execute(
        select(OpportunityReport).where(OpportunityReport.id == opportunity_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Opportunity report not found")

    # 创建 ContentProduct 记录
    product = ContentProduct(
        opportunity_id=opportunity_id,
        product_type=request.product_type,
        status="pending",
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)

    # 将 opportunity 转为 dict（安全处理 None 和错误类型）
    monetization = report.monetization_strategy
    if not isinstance(monetization, dict):
        monetization = {}
    opp_data = {
        "topic": report.topic,
        "core_emotions": report.core_emotions,
        "core_pain_points": report.core_pain_points,
        "willingness_to_pay": report.willingness_to_pay,
        "audience_profile": report.audience_profile or "",
        "hook_lines": report.hook_lines or [],
        "viral_formula": monetization.get("viral_formula", ""),
        "identity_factor": "",
    }

    # 入队 ARQ
    redis = await arq.create_pool(WorkerSettings.redis_settings)
    job = await redis.enqueue_job(
        "generate_content_product",
        product_id=str(product.id),
        opportunity_data=opp_data,
        product_type=request.product_type,
    )
    await redis.aclose()

    return {
        "status": "queued",
        "product_id": str(product.id),
        "job_id": job.job_id if job else None,
        "product_type": request.product_type,
        "message": f"{request.product_type} generation queued",
    }


@router.get("/opportunities/{opportunity_id}/products", response_model=list[ProductResponse])
async def list_products(
    opportunity_id: str,
    session: AsyncSession = Depends(get_db),
):
    """获取某商机下生成的所有产品"""
    result = await session.execute(
        select(ContentProduct).where(ContentProduct.opportunity_id == opportunity_id)
    )
    return list(result.scalars().all())


@router.post("/opportunities/{opportunity_id}/products/{product_id}/tts")
async def trigger_tts(
    opportunity_id: str,
    product_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """触发视频脚本配音生成"""
    from backend.db.redis import get_redis_settings
    import arq

    # 验证产品存在且是 short_video_scripts 类型
    result = await session.execute(
        select(ContentProduct).where(
            ContentProduct.id == product_id,
            ContentProduct.opportunity_id == opportunity_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.product_type != "short_video_scripts":
        raise HTTPException(status_code=400, detail="TTS only for short_video_scripts")
    if product.status != "ready":
        raise HTTPException(status_code=400, detail=f"Product not ready, status={product.status}")
    if product.tts_status in ("generating", "ready"):
        return {
            "status": product.tts_status,
            "product_id": product_id,
            "message": "TTS already in progress or done",
            "tts_audio_urls": product.tts_audio_urls,
        }

    # 更新状态为 pending 并入队
    product.tts_status = "pending"
    await session.commit()

    pool = await arq.create_pool(get_redis_settings())
    job = await pool.enqueue_job("generate_tts_audio", product_id)
    await pool.aclose()

    return {
        "status": "queued",
        "product_id": product_id,
        "job_id": job.job_id if job else None,
        "message": "TTS generation queued",
    }


@router.get("/opportunities/{opportunity_id}/products/{product_id}/tts")
async def get_tts_status(
    opportunity_id: str,
    product_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """查询配音状态"""
    result = await session.execute(
        select(ContentProduct).where(
            ContentProduct.id == product_id,
            ContentProduct.opportunity_id == opportunity_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "product_id": product_id,
        "tts_status": product.tts_status,
        "tts_audio_urls": product.tts_audio_urls or [],
        "tts_error": product.tts_error,
    }
