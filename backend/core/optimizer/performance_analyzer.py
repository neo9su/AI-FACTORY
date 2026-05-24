"""Phase 5-C — 内容表现分析引擎。

输入:  product_engagements 原始事件 + opportunity_scores 聚合分
输出:  ContentPerformance 记录 + 优化建议
"""
from __future__ import annotations
import logging
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.models.engagement import ProductEngagement
from backend.models.trend import ContentProduct
from backend.models.optimization import ContentPerformance

logger = logging.getLogger(__name__)

# ── 归一化天花板 ──
SATURATION_VIEWS = 1000
SATURATION_ACTIONS = 300


def _normalize(value: float, ceiling: float) -> float:
    return min(10.0, (value / ceiling) * 10.0)


async def analyze_product_performance(
    product_id: str,
    session: AsyncSession,
) -> dict[str, Any]:
    """分析单个产品的表现，返回结构化报告。"""
    # 1. 获取产品信息
    product = await session.scalar(
        select(ContentProduct).where(ContentProduct.id == product_id)
    )
    if not product:
        return {"error": "product_not_found"}

    # 2. 获取聚合事件
    agg_q = (
        select(
            ProductEngagement.event_type,
            func.count(ProductEngagement.id).label("cnt"),
        )
        .where(ProductEngagement.product_id == product_id)
        .group_by(ProductEngagement.event_type)
    )
    agg_result = await session.execute(agg_q)
    events: dict[str, int] = {r.event_type: r.cnt for r in agg_result}

    total_views = events.get("view", 0)
    total_plays = events.get("audio_play", 0)
    total_downloads = events.get("ebook_download", 0)
    total_tests = events.get("test_complete", 0)

    # 3. 计算行为指标
    hook_retention = _normalize(total_plays, SATURATION_ACTIONS) if total_views > 0 else 0.0
    angle_click = _normalize(total_downloads, SATURATION_ACTIONS) if total_views > 0 else 0.0
    format_completion = _normalize(total_tests, SATURATION_ACTIONS) if total_views > 0 else 0.0

    # 4. 衍生指标
    total_actions = total_plays + total_downloads + total_tests
    engagement_efficiency = round((total_actions / max(total_views, 1)) * 100, 2)

    # 5. 等级评定 (S/A/B/C/D)
    composite = hook_retention * 0.4 + angle_click * 0.35 + format_completion * 0.25
    if composite >= 8.0:
        grade = "S"
    elif composite >= 6.0:
        grade = "A"
    elif composite >= 4.0:
        grade = "B"
    elif composite >= 2.0:
        grade = "C"
    else:
        grade = "D"

    # 6. 规则优化建议
    recommendation = _generate_recommendation(
        product_type=product.product_type,
        grade=grade,
        events=events,
    )

    return {
        "product_id": product_id,
        "product_type": product.product_type,
        "total_views": total_views,
        "total_plays": total_plays,
        "total_downloads": total_downloads,
        "total_test_completes": total_tests,
        "hook_retention_rate": round(hook_retention, 2),
        "angle_click_rate": round(angle_click, 2),
        "format_completion_rate": round(format_completion, 2),
        "engagement_efficiency": engagement_efficiency,
        "performance_grade": grade,
        "recommendation": recommendation,
    }


async def analyze_all_products_for_opportunity(
    opportunity_id: str,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """分析某个机会下所有产品的表现。"""
    result = await session.execute(
        select(ContentProduct).where(ContentProduct.opportunity_id == opportunity_id)
    )
    products = result.scalars().all()
    results = []
    for prod in products:
        perf = await analyze_product_performance(str(prod.id), session)
        if "error" not in perf:
            results.append(perf)
    return results


def _generate_recommendation(
    product_type: str,
    grade: str,
    events: dict[str, int],
) -> str:
    """基于规则生成优化建议。"""
    recs = []
    views = events.get("view", 0)
    plays = events.get("audio_play", 0)
    downloads = events.get("ebook_download", 0)

    if views < 10:
        recs.append("曝光不足，建议检查发布时间和标题吸引力")
    elif views > 50 and (plays + downloads) < views * 0.1:
        recs.append("曝光高但互动低，建议优化前3秒钩子和CTA")
    elif plays > 20 and downloads == 0:
        recs.append("完播率好但下载转化为0，建议在结尾加入下载引导")

    if product_type == "ebook" and downloads < 5 and views > 30:
        recs.append("电子书下载率低，建议优化封面的价值主张")
    elif product_type == "personality_test" and events.get("test_complete", 0) < 3:
        recs.append("测试完成率低，建议简化题目或改善结果页面")

    if not recs:
        recs.append(f"表现评级 {grade}，继续保持当前策略")

    return "；".join(recs)


async def upsert_performance_report(
    product_id: str,
    opportunity_id: str | None,
    analysis: dict[str, Any],
    session: AsyncSession,
) -> None:
    """将分析结果写入 ContentPerformance 表。"""
    stmt = (
        pg_insert(ContentPerformance)
        .values(
            product_id=product_id,
            opportunity_id=opportunity_id,
            total_views=analysis.get("total_views", 0),
            total_plays=analysis.get("total_plays", 0),
            total_downloads=analysis.get("total_downloads", 0),
            total_test_completes=analysis.get("total_test_completes", 0),
            hook_retention_rate=analysis.get("hook_retention_rate", 0.0),
            angle_click_rate=analysis.get("angle_click_rate", 0.0),
            format_completion_rate=analysis.get("format_completion_rate", 0.0),
            engagement_efficiency=analysis.get("engagement_efficiency", 0.0),
            recommendation=analysis.get("recommendation"),
            performance_grade=analysis.get("performance_grade", "C"),
        )
        .on_conflict_do_update(
            constraint="content_performances_pkey",
            set_={
                "total_views": analysis.get("total_views", 0),
                "total_plays": analysis.get("total_plays", 0),
                "total_downloads": analysis.get("total_downloads", 0),
                "total_test_completes": analysis.get("total_test_completes", 0),
                "hook_retention_rate": analysis.get("hook_retention_rate", 0.0),
                "angle_click_rate": analysis.get("angle_click_rate", 0.0),
                "format_completion_rate": analysis.get("format_completion_rate", 0.0),
                "engagement_efficiency": analysis.get("engagement_efficiency", 0.0),
                "recommendation": analysis.get("recommendation"),
                "performance_grade": analysis.get("performance_grade", "C"),
                "updated_at": func.now(),
            },
        )
    )
    await session.execute(stmt)
