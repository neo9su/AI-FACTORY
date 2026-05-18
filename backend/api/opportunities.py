"""Opportunities API — 商机报告管理"""
from typing import Optional

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
    """根据商机报告生成内容产品"""
    # 验证商机存在
    result = await session.execute(
        select(OpportunityReport).where(OpportunityReport.id == opportunity_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Opportunity report not found")

    # TODO: Phase 3 Factory 实现后接入
    return {
        "status": "queued",
        "opportunity_id": opportunity_id,
        "product_type": request.product_type,
        "message": f"Product generation queued: {request.product_type}",
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
