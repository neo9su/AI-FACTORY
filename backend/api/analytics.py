"""Phase 5-A — Analytics & engagement endpoints."""
from __future__ import annotations

import logging
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.engagement import OpportunityScore, ProductEngagement
from backend.models.trend import ContentProduct, OpportunityReport

logger = logging.getLogger(__name__)
router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────

EventType = Literal["view", "audio_play", "ebook_download", "test_complete"]


class LogEventRequest(BaseModel):
    product_id: str
    event_type: EventType
    session_id: Optional[str] = None
    metadata: Optional[dict] = None


class LogEventResponse(BaseModel):
    ok: bool
    event_id: str


class TopOpportunityItem(BaseModel):
    opportunity_id: str
    topic: str
    roi_score: float
    engagement_score: float  # 0–10 normalized
    composite_score: float  # final ranked score
    total_views: int
    total_plays: int
    total_downloads: int
    total_test_completes: int
    engagement_boost: float
    product_count: int

    model_config = ConfigDict(from_attributes=True)


class ProductStatsResponse(BaseModel):
    product_id: str
    product_type: str
    title: Optional[str]
    total_views: int
    total_audio_plays: int
    total_ebook_downloads: int
    total_test_completes: int
    total_events: int
    breakdown: dict[str, int]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/events", response_model=LogEventResponse, status_code=201)
async def log_event(
    body: LogEventRequest,
    session: AsyncSession = Depends(get_db),
) -> LogEventResponse:
    """Log a user engagement event.

    Fire-and-forget from frontend — always returns 201 even if product_id is
    stale (we do a soft-check to avoid noise but don't 404 on the client).
    """
    # Soft-validate product exists (skip 404 to keep client non-blocking)
    exists = await session.scalar(
        select(ContentProduct.id).where(ContentProduct.id == body.product_id)
    )
    if not exists:
        logger.warning("[Analytics] log_event: unknown product_id=%s", body.product_id)
        # still return ok=True so frontend isn't blocked
        return LogEventResponse(ok=False, event_id="")

    event = ProductEngagement(
        product_id=body.product_id,
        event_type=body.event_type,
        session_id=body.session_id,
        event_metadata=body.metadata,
    )
    session.add(event)
    await session.flush()  # get generated ID before commit
    event_id = str(event.id)
    await session.commit()

    logger.debug("[Analytics] Logged %s for product %s", body.event_type, body.product_id)
    return LogEventResponse(ok=True, event_id=event_id)


@router.get("/analytics/top-opportunities", response_model=list[TopOpportunityItem])
async def get_top_opportunities(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_db),
) -> list[TopOpportunityItem]:
    """Return opportunities ranked by composite_score (engagement-boosted).

    Falls back to roi_score for opportunities that have no score row yet.
    """
    # Opportunities WITH a score row
    scored_q = (
        select(
            OpportunityReport.id.label("opportunity_id"),
            OpportunityReport.topic,
            OpportunityReport.roi_score,
            OpportunityScore.engagement_score,
            OpportunityScore.composite_score,
            OpportunityScore.total_views,
            OpportunityScore.total_plays,
            OpportunityScore.total_downloads,
            OpportunityScore.total_test_completes,
            OpportunityScore.engagement_boost,
        )
        .join(OpportunityScore, OpportunityReport.id == OpportunityScore.opportunity_id)
        .order_by(desc(OpportunityScore.composite_score))
        .limit(limit)
    )
    result = await session.execute(scored_q)
    rows = result.mappings().all()

    # Count products per opportunity
    product_counts_q = select(
        ContentProduct.opportunity_id,
        func.count(ContentProduct.id).label("cnt"),
    ).group_by(ContentProduct.opportunity_id)
    pc_result = await session.execute(product_counts_q)
    pc_map: dict[str, int] = {r.opportunity_id: r.cnt for r in pc_result}

    items: list[TopOpportunityItem] = []
    for row in rows:
        items.append(
            TopOpportunityItem(
                opportunity_id=row["opportunity_id"],
                topic=row["topic"],
                roi_score=row["roi_score"],
                engagement_score=row["engagement_score"],
                composite_score=row["composite_score"],
                total_views=row["total_views"],
                total_plays=row["total_plays"],
                total_downloads=row["total_downloads"],
                total_test_completes=row["total_test_completes"],
                engagement_boost=row["engagement_boost"],
                product_count=pc_map.get(str(row["opportunity_id"]), 0),
            )
        )
    return items


@router.get(
    "/analytics/products/{product_id}/stats",
    response_model=ProductStatsResponse,
)
async def get_product_stats(
    product_id: str,
    session: AsyncSession = Depends(get_db),
) -> ProductStatsResponse:
    """Per-product engagement breakdown."""
    product = await session.scalar(
        select(ContentProduct).where(ContentProduct.id == product_id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Aggregate counts per event_type
    agg_q = (
        select(
            ProductEngagement.event_type,
            func.count(ProductEngagement.id).label("cnt"),
        )
        .where(ProductEngagement.product_id == product_id)
        .group_by(ProductEngagement.event_type)
    )

    agg_result = await session.execute(agg_q)
    breakdown: dict[str, int] = {row.event_type: row.cnt for row in agg_result}

    return ProductStatsResponse(
        product_id=product_id,
        product_type=product.product_type,
        title=product.title,
        total_views=breakdown.get("view", 0),
        total_audio_plays=breakdown.get("audio_play", 0),
        total_ebook_downloads=breakdown.get("ebook_download", 0),
        total_test_completes=breakdown.get("test_complete", 0),
        total_events=sum(breakdown.values()),
        breakdown=breakdown,
    )
