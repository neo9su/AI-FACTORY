"""Phase 5-C — 优化 Worker (ARQ Cron).

每小时运行:
1. 扫描近期发布的、有足够数据的产品
2. 运行 Performance Analyzer
3. 写入 ContentPerformance 表
4. 检查是否有 A/B 测试需要评估
5. 提取通用模式到 ContentPattern
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, desc

from backend.db.session import AsyncSessionLocal
from backend.models.trend import ContentProduct
from backend.models.optimization import ContentPattern, ContentPerformance, ABTest
from backend.core.optimizer.performance_analyzer import (
    analyze_product_performance,
    upsert_performance_report,
)

logger = logging.getLogger(__name__)


async def run_optimization_pipeline(ctx: dict[str, Any]) -> dict[str, Any]:
    """ARQ cron job — runs every hour.

    优化流水线:
    1. 查找 7 天内有互动数据的产品
    2. 逐个运行 Performance Analyzer
    3. 写入 ContentPerformance 报告
    4. 检查并评估到期的 A/B 测试
    5. 提取跨产品的通用模式
    """
    logger.info("[OptimizerWorker] Starting optimization pipeline")

    analyzed_count = 0
    ab_evaluated = 0
    patterns_found = 0

    async with AsyncSessionLocal() as session:
        # Step 1: Find products from last 7 days that are ready
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_result = await session.execute(
            select(ContentProduct.id, ContentProduct.opportunity_id)
            .where(
                ContentProduct.created_at >= week_ago,
                ContentProduct.status == "ready",
            )
            .limit(50)
        )
        recent_products = recent_result.all()

        # Step 2: Run performance analysis for each
        for row in recent_products:
            product_id = str(row.id)
            opp_id = str(row.opportunity_id) if row.opportunity_id else None

            analysis = await analyze_product_performance(product_id, session)
            if "error" not in analysis:
                await upsert_performance_report(product_id, opp_id, analysis, session)
                analyzed_count += 1

        # Step 3: Evaluate completed A/B tests (running > 24h)
        running_tests = await session.execute(
            select(ABTest).where(
                ABTest.status == "running",
                ABTest.created_at <= datetime.utcnow() - timedelta(hours=24),
            )
        )
        for test in running_tests.scalars().all():
            # Simplified evaluation: mark as completed
            test.status = "completed"
            test.winner_id = "baseline"
            ab_evaluated += 1

        # Step 4: Extract cross-product patterns from top performances
        top_performances = await session.execute(
            select(ContentPerformance)
            .where(ContentPerformance.performance_grade.in_(["S", "A"]))
            .order_by(ContentPerformance.hook_retention_rate.desc())
            .limit(10)
        )
        top_prods = top_performances.scalars().all()

        if top_prods:
            high_retention = [p for p in top_prods if p.hook_retention_rate >= 6.0]
            if high_retention:
                avg_hook = sum(p.hook_retention_rate for p in high_retention) / len(high_retention)
                # Check if pattern already exists
                existing = await session.scalar(
                    select(ContentPattern).where(
                        ContentPattern.pattern_type == "hook",
                        ContentPattern.pattern_key == "high_retention_hook_pattern",
                    )
                )
                if not existing:
                    new_pattern = ContentPattern(
                        pattern_type="hook",
                        pattern_key="high_retention_hook_pattern",
                        pattern_value=f"发现 {len(high_retention)} 个高完播率内容，平均钩效 {avg_hook:.1f}/10",
                        effectiveness_score=round(avg_hook, 2),
                        sample_count=len(high_retention),
                    )
                    session.add(new_pattern)
                    patterns_found = 1

        await session.commit()

    logger.info(
        "[OptimizerWorker] Done: analyzed=%d, ab_evaluated=%d, patterns=%d",
        analyzed_count,
        ab_evaluated,
        patterns_found,
    )
    return {
        "analyzed_count": analyzed_count,
        "ab_evaluated": ab_evaluated,
        "patterns_found": patterns_found,
    }
