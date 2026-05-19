"""Phase 5-A — Hourly engagement score recalculation worker."""
from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.db.session import AsyncSessionLocal
from backend.models.engagement import OpportunityScore, ProductEngagement
from backend.models.trend import ContentProduct, OpportunityReport

logger = logging.getLogger(__name__)

# Threshold: if total views across all of an opportunity's products
# exceeds this value, auto-queue a new content generation job.
REGEN_THRESHOLD: int = int(os.getenv("ENGAGEMENT_REGEN_THRESHOLD", "50"))

# Normalization ceiling: views count above which engagement_score saturates at 10
SATURATION_VIEWS: int = int(os.getenv("SCORE_NORMALIZATION_VIEWS", "500"))
SATURATION_PLAYS: int = int(os.getenv("SCORE_NORMALIZATION_PLAYS", "200"))
SATURATION_DOWNLOADS: int = int(os.getenv("SCORE_NORMALIZATION_DOWNLOADS", "100"))
SATURATION_TEST_COMPLETES: int = int(os.getenv("SCORE_NORMALIZATION_TESTS", "150"))


def _normalize(value: float, ceiling: float) -> float:
    """Map [0, ceiling] → [0, 10] with soft saturation."""
    return min(10.0, (value / ceiling) * 10.0)


async def recalculate_scores(ctx: dict[str, Any]) -> dict[str, Any]:
    """ARQ cron job — runs every hour.

    Algorithm:
    1. For each OpportunityReport:
       a. Collect all ContentProduct IDs under it
       b. SUM engagement events (grouped by event_type)
       c. Compute normalized engagement_score
       d. composite = roi_score * 0.6 + engagement_score * 0.4
       e. UPSERT into opportunity_scores
    2. Check each opportunity's total_views against REGEN_THRESHOLD
       → if exceeded: enqueue generate_content_product for its best_product type

    Returns:
        dict with updated_count, regen_triggered_count
    """
    logger.info("[ScoreWorker] Starting recalculate_scores")
    updated_count = 0
    regen_triggered: list[str] = []

    async with AsyncSessionLocal() as session:
        # --- Step 1: All opportunities ---
        opps_result = await session.execute(
            select(
                OpportunityReport.id,
                OpportunityReport.roi_score,
                OpportunityReport.best_product,
                OpportunityReport.topic,
            )
        )
        opportunities = opps_result.mappings().all()

        # --- Step 2: All product → opportunity mapping ---
        prod_q = select(
            ContentProduct.id,
            ContentProduct.opportunity_id,
            ContentProduct.product_type,
            ContentProduct.status,
        )
        prod_result = await session.execute(prod_q)
        products = prod_result.mappings().all()

        # Build map: opportunity_id → list of product_ids
        opp_to_products: dict[str, list[str]] = {}
        prod_meta: dict[str, dict] = {}  # product_id → {type, status}
        for p in products:
            opp_to_products.setdefault(str(p["opportunity_id"]), []).append(str(p["id"]))
            prod_meta[str(p["id"])] = {
                "type": p["product_type"],
                "status": p["status"],
                "opportunity_id": str(p["opportunity_id"]),
            }

        # --- Step 3: Aggregate all events at once ---
        agg_q = select(
            ProductEngagement.product_id,
            ProductEngagement.event_type,
            func.count(ProductEngagement.id).label("cnt"),
        ).group_by(
            ProductEngagement.product_id,
            ProductEngagement.event_type,
        )
        agg_result = await session.execute(agg_q)

        # Build map: product_id → {event_type: count}
        product_events: dict[str, dict[str, int]] = {}
        for row in agg_result.mappings():
            pid = str(row["product_id"])
            product_events.setdefault(pid, {})[row["event_type"]] = row["cnt"]

        # --- Step 4: Compute & upsert per opportunity ---
        for opp in opportunities:
            opp_id = str(opp["id"])
            roi = float(opp["roi_score"] or 0.0)

            # Sum events across all products of this opportunity
            total_views = 0
            total_plays = 0
            total_downloads = 0
            total_tests = 0

            for pid in opp_to_products.get(opp_id, []):
                evts = product_events.get(pid, {})
                total_views += evts.get("view", 0)
                total_plays += evts.get("audio_play", 0)
                total_downloads += evts.get("ebook_download", 0)
                total_tests += evts.get("test_complete", 0)

            # Weighted engagement score
            eng = (
                _normalize(total_views, SATURATION_VIEWS) * 0.40
                + _normalize(total_plays, SATURATION_PLAYS) * 0.30
                + _normalize(total_downloads, SATURATION_DOWNLOADS) * 0.20
                + _normalize(total_tests, SATURATION_TEST_COMPLETES) * 0.10
            )
            # Scale back to 0–10 range (weighted avg of 0–10 components)
            engagement_score = round(eng, 4)
            engagement_boost = round(engagement_score * 0.4, 4)
            composite_score = round(roi * 0.6 + engagement_score * 0.4, 4)

            # UPSERT (PostgreSQL ON CONFLICT DO UPDATE)
            stmt = (
                pg_insert(OpportunityScore)
                .values(
                    opportunity_id=opp_id,
                    total_views=total_views,
                    total_plays=total_plays,
                    total_downloads=total_downloads,
                    total_test_completes=total_tests,
                    engagement_score=engagement_score,
                    engagement_boost=engagement_boost,
                    composite_score=composite_score,
                )
                .on_conflict_do_update(
                    index_elements=["opportunity_id"],
                    set_={
                        "total_views": total_views,
                        "total_plays": total_plays,
                        "total_downloads": total_downloads,
                        "total_test_completes": total_tests,
                        "engagement_score": engagement_score,
                        "engagement_boost": engagement_boost,
                        "composite_score": composite_score,
                        "updated_at": func.now(),
                    },
                )
            )
            await session.execute(stmt)
            updated_count += 1

            # --- Step 5: Auto-regen trigger ---
            if total_views >= REGEN_THRESHOLD:
                # Avoid duplicate re-gen if one already in progress
                in_progress = any(
                    prod_meta[pid]["status"] in ("pending", "generating")
                    for pid in opp_to_products.get(opp_id, [])
                )
                if not in_progress:
                    regen_triggered.append(opp_id)
                    logger.info(
                        "[ScoreWorker] Triggering regen for opportunity %s "
                        "(views=%d >= threshold=%d)",
                        opp_id,
                        total_views,
                        REGEN_THRESHOLD,
                    )

        await session.commit()

    # Enqueue regen jobs AFTER DB commit (outside session)
    if regen_triggered:
        await _enqueue_regen_jobs(regen_triggered, prod_meta, opp_to_products)

    logger.info(
        "[ScoreWorker] Done: updated=%d, regen_triggered=%d",
        updated_count,
        len(regen_triggered),
    )
    return {
        "updated_count": updated_count,
        "regen_triggered": regen_triggered,
    }


async def _enqueue_regen_jobs(
    opp_ids: list[str],
    prod_meta: dict[str, dict],
    opp_to_products: dict[str, list[str]],
) -> None:
    """Enqueue a new generate_content_product job for each flagged opportunity."""
    import arq

    from backend.workers.pipeline import WorkerSettings

    async with AsyncSessionLocal() as session:
        for opp_id in opp_ids:
            # Re-fetch opportunity for data
            opp = await session.scalar(
                select(OpportunityReport).where(OpportunityReport.id == opp_id)
            )
            if not opp:
                continue

            # Create new ContentProduct record
            product_type = str(opp.best_product or "ebook")
            new_product = ContentProduct(
                opportunity_id=opp_id,
                product_type=product_type,
                status="pending",
                meta={"triggered_by": "feedback_loop", "regen": True},
            )
            session.add(new_product)
            await session.flush()

        await session.commit()

    # Now enqueue ARQ jobs
    redis = await arq.create_pool(WorkerSettings.redis_settings)
    async with AsyncSessionLocal() as session:
        for opp_id in opp_ids:
            opp = await session.scalar(
                select(OpportunityReport).where(OpportunityReport.id == opp_id)
            )
            if not opp:
                continue
            opp_data = {
                "topic": opp.topic,
                "core_emotions": opp.core_emotions,
                "core_pain_points": opp.core_pain_points,
                "willingness_to_pay": opp.willingness_to_pay,
                "audience_profile": opp.audience_profile,
                "hook_lines": opp.hook_lines,
                "viral_formula": (opp.monetization_strategy or {}).get("viral_formula", ""),
                "identity_factor": "",
            }
            # Find the newly created pending product for this opp
            new_prod = await session.scalar(
                select(ContentProduct)
                .where(
                    ContentProduct.opportunity_id == opp_id,
                    ContentProduct.status == "pending",
                )
                .order_by(desc(ContentProduct.created_at))
                .limit(1)
            )
            if new_prod:
                await redis.enqueue_job(
                    "generate_content_product",
                    product_id=str(new_prod.id),
                    opportunity_data=opp_data,
                    product_type=str(opp.best_product or "ebook"),
                )
    await redis.aclose()
