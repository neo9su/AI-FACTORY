"""NeuroTrend 异步工作队列 — Hunter -> Brain -> Strategist 流水线"""
from __future__ import annotations

import logging
from typing import Any

from backend.core.brain.emotion_analyzer import EmotionAnalyzer
from backend.core.hunter.reddit_hunter import RedditHunter
from backend.core.strategist.opportunity_generator import OpportunityGenerator
from backend.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_trend_scan(ctx: dict[str, Any], sources: list[str] | None = None) -> dict:
    """完整的 Hunter -> Brain -> Strategist 流水线

    Args:
        ctx: ARQ worker context
        sources: 数据源列表, 默认 ["reddit"]

    Returns:
        dict with keys: scanned, opportunities_generated
    """
    if sources is None:
        sources = ["reddit"]

    logger.info(f"[TrendScan] Starting scan, sources={sources}")

    # Step 1: Hunter — 抓取原始热点信号
    all_signals = []
    if "reddit" in sources:
        hunter = RedditHunter()
        signals = await hunter.hunt(limit=10)
        all_signals.extend(signals)
        logger.info(f"[TrendScan] Fetched {len(signals)} signals from Reddit")

    if not all_signals:
        logger.warning("[TrendScan] No signals fetched")
        return {"scanned": 0, "opportunities_generated": 0}

    # Step 2: 保存原始信号到 DB
    from backend.models.trend import TrendSignal

    saved_signals: list[tuple[Any, TrendSignal]] = []
    async with AsyncSessionLocal() as session:
        for raw in all_signals:
            db_signal = TrendSignal(
                source=raw.source,
                title=raw.title,
                url=raw.url,
                raw_content=raw.content,
                engagement_score=raw.engagement_score,
            )
            session.add(db_signal)
            saved_signals.append((raw, db_signal))
        await session.commit()
        # Refresh to get generated IDs
        for _, db_signal in saved_signals:
            await session.refresh(db_signal)
        logger.info(f"[TrendScan] Saved {len(all_signals)} signals to DB")

    # Step 3: Brain — 情绪分析 (top 5 by engagement)
    analyzer = EmotionAnalyzer()
    top_raws = sorted(all_signals, key=lambda x: x.engagement_score, reverse=True)[:5]
    analyzed_results = await analyzer.batch_analyze(top_raws, top_n=5)

    # Build lookup: title -> db_signal.id
    title_to_id: dict[str, str] = {raw.title: db.id for raw, db in saved_signals}

    # Step 4: Strategist — 生成商机报告并保存
    from backend.models.trend import OpportunityReport

    generator = OpportunityGenerator()
    opportunities_generated = 0

    async with AsyncSessionLocal() as session:
        for signal, emotion_data in analyzed_results:
            if "error" in emotion_data:
                logger.warning(f"[TrendScan] Skip '{signal.title[:40]}': emotion error")
                continue

            opportunity = await generator.generate_and_score(signal.title, emotion_data)
            if "error" in opportunity:
                logger.warning(f"[TrendScan] Skip '{signal.title[:40]}': opportunity error")
                continue

            products = opportunity.get("product_suggestions", [])
            market = opportunity.get("market_analysis", {})
            report = OpportunityReport(
                trend_signal_id=title_to_id.get(signal.title),
                topic=signal.title,
                why_viral=opportunity.get("why_viral", ""),
                core_emotions=opportunity.get("core_emotions", []),
                core_pain_points=opportunity.get("core_pain_points", []),
                willingness_to_pay=opportunity.get("willingness_to_pay", ""),
                product_suggestions=products,
                best_product=opportunity.get("best_product", ""),
                roi_score=float(products[0].get("roi_score", 0)) if products else 0.0,
                automation_score=float(products[0].get("automation_score", 0)) if products else 0.0,
                seo_value=market.get("seo_value"),
                lifecycle=market.get("lifecycle"),
                hook_lines=opportunity.get("hook_lines", []),
                content_angles=opportunity.get("content_angles", []),
                monetization_strategy=opportunity.get("monetization_strategy"),
                action_plan=opportunity.get("action_plan"),
                audience_profile=opportunity.get("audience_profile", ""),
            )
            session.add(report)
            opportunities_generated += 1

        await session.commit()
        logger.info(f"[TrendScan] Generated {opportunities_generated} opportunities")

    return {"scanned": len(all_signals), "opportunities_generated": opportunities_generated}


async def analyze_single_trend(ctx: dict[str, Any], trend_signal_id: str) -> dict:
    """分析单个热点信号，运行 Brain + Strategist 并保存商机报告

    Args:
        ctx: ARQ worker context
        trend_signal_id: TrendSignal 的 UUID

    Returns:
        dict with keys: opportunity_id, topic  — or error details
    """
    from sqlalchemy import select

    from backend.core.hunter.base import RawSignal
    from backend.models.trend import OpportunityReport, TrendSignal

    # 从 DB 加载信号
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TrendSignal).where(TrendSignal.id == trend_signal_id)
        )
        db_signal = result.scalar_one_or_none()
        if not db_signal:
            logger.error(f"[SingleTrend] TrendSignal {trend_signal_id} not found")
            return {"error": f"TrendSignal {trend_signal_id} not found"}

        signal = RawSignal(
            source=db_signal.source,
            title=db_signal.title,
            content=db_signal.raw_content or "",
            url=db_signal.url or "",
            engagement_score=db_signal.engagement_score,
            raw_data={},
        )

    logger.info(f"[SingleTrend] Analyzing: '{signal.title[:60]}'")

    # Brain — 情绪分析（单条用更强的模型）
    analyzer = EmotionAnalyzer(model=EmotionAnalyzer.SINGLE_MODEL)
    emotion_data = await analyzer.analyze(signal)
    if "error" in emotion_data:
        logger.error(f"[SingleTrend] Emotion analysis failed: {emotion_data}")
        return {"error": "emotion_analysis_failed", "details": emotion_data}

    # Strategist — 生成商机报告
    generator = OpportunityGenerator()
    opportunity = await generator.generate_and_score(signal.title, emotion_data)
    if "error" in opportunity:
        logger.error(f"[SingleTrend] Opportunity generation failed: {opportunity}")
        return {"error": "opportunity_generation_failed", "details": opportunity}

    # 保存商机报告
    products = opportunity.get("product_suggestions", [])
    market = opportunity.get("market_analysis", {})
    async with AsyncSessionLocal() as session:
        report = OpportunityReport(
            trend_signal_id=trend_signal_id,
            topic=signal.title,
            why_viral=opportunity.get("why_viral", ""),
            core_emotions=opportunity.get("core_emotions", []),
            core_pain_points=opportunity.get("core_pain_points", []),
            willingness_to_pay=opportunity.get("willingness_to_pay", ""),
            product_suggestions=products,
            best_product=opportunity.get("best_product", ""),
            roi_score=float(products[0].get("roi_score", 0)) if products else 0.0,
            automation_score=float(products[0].get("automation_score", 0)) if products else 0.0,
            seo_value=market.get("seo_value"),
            lifecycle=market.get("lifecycle"),
            hook_lines=opportunity.get("hook_lines", []),
            content_angles=opportunity.get("content_angles", []),
            monetization_strategy=opportunity.get("monetization_strategy"),
            action_plan=opportunity.get("action_plan"),
            audience_profile=opportunity.get("audience_profile", ""),
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        logger.info(f"[SingleTrend] Saved OpportunityReport {report.id}")
        return {"opportunity_id": str(report.id), "topic": signal.title}
