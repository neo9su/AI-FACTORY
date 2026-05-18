"""Opportunities API — 商机报告管理"""
from __future__ import annotations

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


@router.get("/opportunities", response_model=list[OpportunityResponse])
async def list_opportunities(
    min_roi: float = 0.0,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
) -> list[OpportunityReport]:
    """获取商机报告列表（按ROI排序）"""
    query = (
        select(OpportunityReport)
        .where(OpportunityReport.roi_score >= min_roi)
        .order_by(desc(OpportunityReport.roi_score))
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/opportunities/{opportunity_id}")
async def get_opportunity(
    opportunity_id: str,
    session: AsyncSession = Depends(get_db),
) -> OpportunityReport:
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

    # 将 opportunity 转为 dict
    opp_data = {
        "topic": report.topic,
        "core_emotions": report.core_emotions,
        "core_pain_points": report.core_pain_points,
        "willingness_to_pay": report.willingness_to_pay,
        "audience_profile": report.audience_profile,
        "hook_lines": report.hook_lines,
        "viral_formula": (report.monetization_strategy or {}).get("viral_formula", ""),
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


@router.get("/opportunities/{opportunity_id}/products")
async def list_products(
    opportunity_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[ContentProduct]:
    """获取某商机下生成的所有产品"""
    result = await session.execute(
        select(ContentProduct).where(ContentProduct.opportunity_id == opportunity_id)
    )
    return list(result.scalars().all())
