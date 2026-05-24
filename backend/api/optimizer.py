"""Phase 5-C — 优化 API 端点。"""
from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.optimization import ContentPerformance, ContentPattern
from backend.models.trend import ContentProduct
from backend.core.optimizer.performance_analyzer import (
    analyze_product_performance,
    analyze_all_products_for_opportunity,
    upsert_performance_report,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ProductPerformanceResponse(BaseModel):
    product_id: str
    product_type: str
    total_views: int
    total_plays: int
    total_downloads: int
    total_test_completes: int
    hook_retention_rate: float
    angle_click_rate: float
    format_completion_rate: float
    engagement_efficiency: float
    performance_grade: str
    recommendation: str | None

    model_config = ConfigDict(from_attributes=True)


class OpportunityOptimizationReport(BaseModel):
    opportunity_id: str
    total_products: int
    grade_distribution: dict[str, int]
    average_engagement_efficiency: float
    top_recommendations: list[str]
    products: list[ProductPerformanceResponse]

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/optimizer/products/{product_id}/performance",
    response_model=ProductPerformanceResponse,
)
async def get_product_performance(
    product_id: str,
    refresh: bool = Query(False, description="重新计算而非读取缓存"),
    session: AsyncSession = Depends(get_db),
) -> ProductPerformanceResponse:
    """获取单个产品的表现分析。"""
    product = await session.scalar(
        select(ContentProduct).where(ContentProduct.id == product_id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if refresh:
        analysis = await analyze_product_performance(product_id, session)
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
        await upsert_performance_report(
            product_id,
            str(product.opportunity_id) if product.opportunity_id else None,
            analysis,
            session,
        )
        await session.commit()
        return ProductPerformanceResponse(**analysis)
    else:
        perf = await session.scalar(
            select(ContentPerformance)
            .where(ContentPerformance.product_id == product_id)
            .order_by(desc(ContentPerformance.created_at))
            .limit(1)
        )
        if not perf:
            raise HTTPException(status_code=404, detail="No performance data yet")

        return ProductPerformanceResponse(
            product_id=str(perf.product_id),
            product_type=product.product_type,
            total_views=perf.total_views,
            total_plays=perf.total_plays,
            total_downloads=perf.total_downloads,
            total_test_completes=perf.total_test_completes,
            hook_retention_rate=perf.hook_retention_rate,
            angle_click_rate=perf.angle_click_rate,
            format_completion_rate=perf.format_completion_rate,
            engagement_efficiency=perf.engagement_efficiency,
            performance_grade=perf.performance_grade,
            recommendation=perf.recommendation,
        )


@router.get(
    "/optimizer/opportunities/{opportunity_id}/report",
    response_model=OpportunityOptimizationReport,
)
async def get_opportunity_optimization_report(
    opportunity_id: str,
    session: AsyncSession = Depends(get_db),
) -> OpportunityOptimizationReport:
    """获取某个机会的全局优化报告（所有产品的表现汇总）。"""
    results = await analyze_all_products_for_opportunity(opportunity_id, session)

    grades: dict[str, int] = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    for r in results:
        grades[r.get("performance_grade", "C")] += 1

    top_recs = [r["recommendation"] for r in results if r.get("recommendation")]
    avg_eff = round(
        sum(r.get("engagement_efficiency", 0) for r in results) / max(len(results), 1), 2
    )

    products = [ProductPerformanceResponse(**r) for r in results]

    return OpportunityOptimizationReport(
        opportunity_id=opportunity_id,
        total_products=len(results),
        grade_distribution=grades,
        average_engagement_efficiency=avg_eff,
        top_recommendations=top_recs[:5],
        products=products,
    )


@router.get("/optimizer/patterns")
async def get_content_patterns(
    pattern_type: Optional[str] = Query(None, description="按类型过滤: hook/angle/format/timing"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """获取系统发现的通用内容模式。"""
    q = (
        select(ContentPattern)
        .order_by(desc(ContentPattern.effectiveness_score))
        .limit(limit)
    )
    if pattern_type:
        q = q.where(ContentPattern.pattern_type == pattern_type)

    result = await session.execute(q)
    patterns = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "pattern_type": p.pattern_type,
            "pattern_key": p.pattern_key,
            "pattern_value": p.pattern_value,
            "effectiveness_score": p.effectiveness_score,
            "sample_count": p.sample_count,
            "emotion_tags": p.emotion_tags,
        }
        for p in patterns
    ]
