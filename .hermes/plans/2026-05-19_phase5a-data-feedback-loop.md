# Phase 5-A: Data Feedback Loop — Implementation Plan

> **Date:** 2026-05-19  
> **Phase:** 5-A — Engagement Tracking → Score Re-ranking → Automated Regeneration  
> **Owner:** NeuroTrend AI Factory  
> **Stack:** FastAPI + Next.js 14 + PostgreSQL + Redis + ARQ

---

## 1. Overview & Architecture

The feedback loop closes the gap between "content generated" and "content that actually performs well." It instruments all user-facing interactions, stores them in two new tables, re-ranks opportunities every hour, and auto-queues high-signal products for regeneration.

```
User action (view / play / download / test)
        │
        ▼
POST /api/v1/events          ← fire-and-forget, <5ms
        │
        ▼
product_engagements (DB)     ← raw event log
        │
        ▼  (ARQ cron, every 60 min)
recalculate_scores()
        │
        ├── aggregate views/plays/downloads per product
        ├── normalize → engagement_score [0–10]
        ├── composite = roi_score×0.6 + engagement_score×0.4
        ├── upsert opportunity_scores
        └── if product.views > REGEN_THRESHOLD → enqueue generate_content_product

        ▼
GET /api/v1/analytics/top-opportunities   ← sorted by composite_score
GET /api/v1/analytics/products/{id}/stats ← per-product breakdown

        ▼
Frontend Analytics Tab
  ├── Ranked opportunity list with engagement bars
  └── Per-product stats modal
```

---

## 2. Files To CREATE vs MODIFY

### 2.1 — Files to CREATE (net-new)

| Path | Type | Purpose |
|---|---|---|
| `backend/models/engagement.py` | Python | `ProductEngagement` + `OpportunityScore` ORM models |
| `backend/api/analytics.py` | Python | 3 new API endpoints |
| `backend/workers/score_worker.py` | Python | `recalculate_scores` ARQ job |
| `frontend/app/analytics/page.tsx` | TSX | New analytics route/page |
| `frontend/components/engagement-bar.tsx` | TSX | Reusable bar component |
| `frontend/components/analytics-tab.tsx` | TSX | Tab-switched panel |

### 2.2 — Files to MODIFY

| Path | Changes |
|---|---|
| `backend/models/__init__.py` | Add `ProductEngagement`, `OpportunityScore` to `__all__` |
| `backend/workers/pipeline.py` | Add `recalculate_scores` to `WorkerSettings.functions` + `cron_jobs` |
| `backend/main.py` | Register `analytics.router` |
| `frontend/types/neurotrend.ts` | Add `ProductEngagement`, `OpportunityScore`, analytics response types |
| `frontend/lib/api.ts` | Add `analyticsApi` namespace |
| `frontend/app/opportunities/page.tsx` | Add "Analytics" nav tab link |

---

## 3. DB Models — `backend/models/engagement.py`

### 3.1 Full Model Definition

```python
# backend/models/engagement.py
"""Phase 5-A — Engagement tracking and composite scoring models."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


class ProductEngagement(UUIDMixin, TimestampMixin, Base):
    """Raw engagement event log — one row per user interaction."""

    __tablename__ = "product_engagements"

    # --- core fields ---
    product_id: Mapped[str] = mapped_column(
        ForeignKey("content_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        # allowed values: "view" | "audio_play" | "ebook_download" | "test_complete"
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        # anonymous session UUID from frontend (localStorage)
    )
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        # flexible payload, e.g.:
        # view       → {"referrer": "...", "page": "/opportunities/xxx"}
        # audio_play → {"script_id": 1, "duration_played_s": 45}
        # download   → {"format": "pdf"}
        # test_complete → {"result_type": "INFJ", "score": 82}
    )

    # --- relationships (optional, for lazy joins) ---
    product: Mapped["ContentProduct"] = relationship(  # noqa: F821
        "ContentProduct",
        back_populates="engagements",
        lazy="raise",
    )

    __table_args__ = (
        # Fast aggregation query: product × event_type × created_at
        Index("ix_pe_product_event_ts", "product_id", "event_type", "created_at"),
    )


class OpportunityScore(UUIDMixin, TimestampMixin, Base):
    """Derived composite score for an opportunity, updated hourly by ARQ."""

    __tablename__ = "opportunity_scores"

    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunity_reports.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # one row per opportunity, upserted
        index=True,
    )
    # raw engagement numbers (sum across all products of this opportunity)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_plays: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_downloads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_test_completes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    engagement_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
        # normalized 0–10, computed in score_worker
    )
    engagement_boost: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
        # = engagement_score × 0.4 (the additive boost component)
    )
    composite_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, index=True
        # = original roi_score × 0.6 + engagement_score × 0.4
    )

    # relationships
    opportunity: Mapped["OpportunityReport"] = relationship(  # noqa: F821
        "OpportunityReport",
        back_populates="score",
        lazy="raise",
    )
```

### 3.2 Back-references to Patch into Existing Models

Add to `ContentProduct` in `backend/models/trend.py`:
```python
engagements: Mapped[list["ProductEngagement"]] = relationship(
    "ProductEngagement", back_populates="product", cascade="all, delete-orphan"
)
```

Add to `OpportunityReport` in `backend/models/trend.py`:
```python
score: Mapped[Optional["OpportunityScore"]] = relationship(
    "OpportunityScore", back_populates="opportunity", uselist=False,
    cascade="all, delete-orphan"
)
```

### 3.3 Update `backend/models/__init__.py`

```python
from backend.models.engagement import ProductEngagement, OpportunityScore

__all__ = [
    # ...existing...
    "ProductEngagement",
    "OpportunityScore",
]
```

---

## 4. API Layer — `backend/api/analytics.py`

### 4.1 Full File

```python
# backend/api/analytics.py
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
    roi_score: float                  # original
    engagement_score: float           # 0–10 normalized
    composite_score: float            # final ranked score
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
    breakdown: dict[str, int]         # event_type → count

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
        metadata=body.metadata,
    )
    session.add(event)
    await session.flush()           # get generated ID before commit
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


@router.get("/analytics/products/{product_id}/stats", response_model=ProductStatsResponse)
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
    agg_q = select(
        ProductEngagement.event_type,
        func.count(ProductEngagement.id).label("cnt"),
    ).where(
        ProductEngagement.product_id == product_id
    ).group_by(ProductEngagement.event_type)

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
```

### 4.2 Register in `backend/main.py`

```python
# ADD import:
from backend.api import analytics

# ADD router registration (after opportunities):
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
```

---

## 5. ARQ Worker — `backend/workers/score_worker.py`

### 5.1 Full Implementation

```python
# backend/workers/score_worker.py
"""Phase 5-A — Hourly engagement score recalculation worker."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.db.session import AsyncSessionLocal
from backend.models.engagement import OpportunityScore, ProductEngagement
from backend.models.trend import ContentProduct, OpportunityReport

logger = logging.getLogger(__name__)

# Threshold: if total views across all of an opportunity's products
# exceeds this value, auto-queue a new content generation job.
REGEN_THRESHOLD: int = 50

# Normalization ceiling: views count above which engagement_score saturates at 10
SATURATION_VIEWS: int = 500   # tune as data grows
SATURATION_PLAYS: int = 200
SATURATION_DOWNLOADS: int = 100
SATURATION_TEST_COMPLETES: int = 150


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
            select(OpportunityReport.id, OpportunityReport.roi_score,
                   OpportunityReport.best_product, OpportunityReport.topic)
        )
        opportunities = opps_result.mappings().all()

        # --- Step 2: All product → opportunity mapping ---
        prod_q = select(ContentProduct.id, ContentProduct.opportunity_id,
                        ContentProduct.product_type, ContentProduct.status)
        prod_result = await session.execute(prod_q)
        products = prod_result.mappings().all()

        # Build map: opportunity_id → list of product_ids
        opp_to_products: dict[str, list[str]] = {}
        prod_meta: dict[str, dict] = {}   # product_id → {type, status}
        for p in products:
            opp_to_products.setdefault(str(p["opportunity_id"]), []).append(str(p["id"]))
            prod_meta[str(p["id"])] = {
                "type": p["product_type"],
                "status": p["status"],
                "opportunity_id": str(p["opportunity_id"]),
            }

        # --- Step 3: Aggregate all events at once ---
        agg_q = (
            select(
                ProductEngagement.product_id,
                ProductEngagement.event_type,
                func.count(ProductEngagement.id).label("cnt"),
            ).group_by(
                ProductEngagement.product_id,
                ProductEngagement.event_type,
            )
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
                total_views      += evts.get("view",            0)
                total_plays      += evts.get("audio_play",      0)
                total_downloads  += evts.get("ebook_download",  0)
                total_tests      += evts.get("test_complete",   0)

            # Weighted engagement score
            eng = (
                _normalize(total_views,     SATURATION_VIEWS)      * 0.40 +
                _normalize(total_plays,     SATURATION_PLAYS)       * 0.30 +
                _normalize(total_downloads, SATURATION_DOWNLOADS)   * 0.20 +
                _normalize(total_tests,     SATURATION_TEST_COMPLETES) * 0.10
            )
            # Scale back to 0–10 range (weighted avg of 0–10 components)
            engagement_score = round(eng, 4)
            engagement_boost = round(engagement_score * 0.4, 4)
            composite_score  = round(roi * 0.6 + engagement_score * 0.4, 4)

            # UPSERT (PostgreSQL ON CONFLICT DO UPDATE)
            stmt = pg_insert(OpportunityScore).values(
                opportunity_id=opp_id,
                total_views=total_views,
                total_plays=total_plays,
                total_downloads=total_downloads,
                total_test_completes=total_tests,
                engagement_score=engagement_score,
                engagement_boost=engagement_boost,
                composite_score=composite_score,
            ).on_conflict_do_update(
                index_elements=["opportunity_id"],
                set_={
                    "total_views":          total_views,
                    "total_plays":          total_plays,
                    "total_downloads":      total_downloads,
                    "total_test_completes": total_tests,
                    "engagement_score":     engagement_score,
                    "engagement_boost":     engagement_boost,
                    "composite_score":      composite_score,
                    "updated_at":           func.now(),
                },
            )
            await session.execute(stmt)
            updated_count += 1

            # --- Step 5: Auto-regen trigger ---
            if total_views >= REGEN_THRESHOLD:
                # Only trigger once per opportunity (check for existing ready products)
                existing_product_types = {
                    prod_meta[pid]["type"]
                    for pid in opp_to_products.get(opp_id, [])
                    if prod_meta[pid]["status"] == "ready"
                }
                regen_type = str(opp["best_product"] or "ebook")
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
                        opp_id, total_views, REGEN_THRESHOLD,
                    )

        await session.commit()

    # Enqueue regen jobs AFTER DB commit (outside session)
    if regen_triggered:
        await _enqueue_regen_jobs(regen_triggered, prod_meta, opp_to_products)

    logger.info(
        "[ScoreWorker] Done: updated=%d, regen_triggered=%d",
        updated_count, len(regen_triggered),
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
    from backend.db.session import AsyncSessionLocal
    from sqlalchemy import select
    from backend.models.trend import ContentProduct, OpportunityReport

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
            new_product_id = str(new_product.id)

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
```

### 5.2 Register in `backend/workers/pipeline.py`

```python
# ADD to imports at top:
from backend.workers.score_worker import recalculate_scores

# ADD to WorkerSettings.functions list:
functions = [
    run_project_pipeline,
    run_single_stage,
    run_trend_scan,
    analyze_single_trend,
    generate_content_product,
    generate_tts_audio,
    recalculate_scores,            # ← NEW
]

# ADD cron_jobs list to WorkerSettings class:
cron_jobs = [
    arq.cron(recalculate_scores, hour=None, minute=0),   # every hour at :00
]
```

> **Note:** `arq.cron` import: `from arq import cron`. Add at top of `pipeline.py`.

---

## 6. Frontend — New Components & Page

### 6.1 Types Extension — `frontend/types/neurotrend.ts`

Append to end of file:
```typescript
// ─── Phase 5-A: Analytics Types ──────────────────────────────────────────────

export type EngagementEventType =
  | 'view'
  | 'audio_play'
  | 'ebook_download'
  | 'test_complete'

export interface LogEventRequest {
  product_id: string
  event_type: EngagementEventType
  session_id?: string
  metadata?: Record<string, unknown>
}

export interface TopOpportunityItem {
  opportunity_id: string
  topic: string
  roi_score: number
  engagement_score: number       // 0–10 normalized
  composite_score: number        // ranked score
  total_views: number
  total_plays: number
  total_downloads: number
  total_test_completes: number
  engagement_boost: number
  product_count: number
}

export interface ProductStatsResponse {
  product_id: string
  product_type: string
  title: string | null
  total_views: number
  total_audio_plays: number
  total_ebook_downloads: number
  total_test_completes: number
  total_events: number
  breakdown: Record<string, number>
}
```

### 6.2 API Client Extension — `frontend/lib/api.ts`

Append to end of `api.ts` (before `export default api`):

```typescript
// ─── Phase 5-A: Analytics API ────────────────────────────────────────────────

export const analyticsApi = {
  /**
   * Fire-and-forget engagement event log.
   * Uses a silent best-effort approach — ignores errors to avoid
   * blocking UI interactions.
   */
  logEvent: async (
    productId: string,
    eventType: 'view' | 'audio_play' | 'ebook_download' | 'test_complete',
    sessionId?: string,
    metadata?: Record<string, unknown>,
  ): Promise<void> => {
    try {
      await api.post('/events', {
        product_id: productId,
        event_type: eventType,
        session_id: sessionId,
        metadata,
      })
    } catch {
      // intentionally silent — tracking failure must never break UX
    }
  },

  getTopOpportunities: async (
    limit = 20,
  ): Promise<TopOpportunityItem[]> => {
    const res = await api.get<TopOpportunityItem[]>(
      `/analytics/top-opportunities?limit=${limit}`,
    )
    return res.data
  },

  getProductStats: async (
    productId: string,
  ): Promise<ProductStatsResponse> => {
    const res = await api.get<ProductStatsResponse>(
      `/analytics/products/${productId}/stats`,
    )
    return res.data
  },
}
```

### 6.3 Reusable Component — `frontend/components/engagement-bar.tsx`

```tsx
// frontend/components/engagement-bar.tsx
'use client'

interface EngagementBarProps {
  label: string
  value: number      // raw count
  maxValue: number   // for width normalization
  colorClass?: string
  icon?: string
}

export function EngagementBar({
  label,
  value,
  maxValue,
  colorClass = 'bg-indigo-500',
  icon = '',
}: EngagementBarProps) {
  const pct = maxValue > 0 ? Math.min(100, Math.round((value / maxValue) * 100)) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-white/60">
        <span>{icon && <span className="mr-1">{icon}</span>}{label}</span>
        <span className="font-semibold text-white">{value.toLocaleString()}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/10">
        <div
          className={`h-1.5 rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
```

### 6.4 Analytics Tab Component — `frontend/components/analytics-tab.tsx`

```tsx
// frontend/components/analytics-tab.tsx
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { analyticsApi } from '@/lib/api'
import { type TopOpportunityItem } from '@/types/neurotrend'
import { EngagementBar } from '@/components/engagement-bar'

export function AnalyticsTab() {
  const [items, setItems] = useState<TopOpportunityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    analyticsApi
      .getTopOpportunities(20)
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-red-400 text-sm text-center py-12">⚠ {error}</div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-20 text-indigo-300">
        <p className="text-4xl mb-3">📊</p>
        <p>暂无参与度数据 — 等待用户互动后每小时自动更新</p>
      </div>
    )
  }

  // max composite_score for relative bar sizing
  const maxComposite = Math.max(...items.map((i) => i.composite_score), 1)
  const maxViews     = Math.max(...items.map((i) => i.total_views), 1)

  return (
    <div className="space-y-4">
      {/* Table header */}
      <div className="grid grid-cols-12 gap-2 text-xs text-white/40 font-medium px-4">
        <span className="col-span-4">商机主题</span>
        <span className="col-span-2 text-right">综合评分</span>
        <span className="col-span-2 text-right">ROI</span>
        <span className="col-span-2 text-right">参与度</span>
        <span className="col-span-2 text-right">总浏览</span>
      </div>

      {items.map((item, idx) => (
        <div
          key={item.opportunity_id}
          className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-indigo-500/40 transition-colors"
        >
          {/* Row summary */}
          <div className="grid grid-cols-12 gap-2 items-center mb-3">
            <div className="col-span-4 flex items-center gap-2 min-w-0">
              <span className="text-white/30 text-sm font-bold w-5 shrink-0">
                #{idx + 1}
              </span>
              <Link
                href={`/opportunities/${item.opportunity_id}`}
                className="text-sm font-semibold text-white hover:text-indigo-300 transition-colors line-clamp-2"
              >
                {item.topic}
              </Link>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-emerald-400 font-bold text-sm">
                {item.composite_score.toFixed(2)}
              </span>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-indigo-300 text-sm">
                {item.roi_score.toFixed(1)}
              </span>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-amber-400 text-sm">
                {item.engagement_score.toFixed(2)}
              </span>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-white/60 text-sm">
                {item.total_views.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Composite score bar */}
          <EngagementBar
            label="综合评分"
            value={Math.round(item.composite_score * 10)}
            maxValue={Math.round(maxComposite * 10)}
            colorClass="bg-gradient-to-r from-emerald-500 to-indigo-500"
            icon="🏆"
          />

          {/* Engagement breakdown (collapsible row) */}
          <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-white/5">
            <EngagementBar
              label="浏览"
              value={item.total_views}
              maxValue={maxViews}
              colorClass="bg-blue-500"
              icon="👁"
            />
            <EngagementBar
              label="试听"
              value={item.total_plays}
              maxValue={Math.max(...items.map((i) => i.total_plays), 1)}
              colorClass="bg-purple-500"
              icon="🎵"
            />
            <EngagementBar
              label="下载"
              value={item.total_downloads}
              maxValue={Math.max(...items.map((i) => i.total_downloads), 1)}
              colorClass="bg-amber-500"
              icon="📥"
            />
            <EngagementBar
              label="测试完成"
              value={item.total_test_completes}
              maxValue={Math.max(...items.map((i) => i.total_test_completes), 1)}
              colorClass="bg-rose-500"
              icon="✅"
            />
          </div>

          {/* Product count badge */}
          <div className="mt-2 text-xs text-white/30">
            {item.product_count} 个内容产品 ·{' '}
            参与度加成 +{item.engagement_boost.toFixed(2)}
          </div>
        </div>
      ))}
    </div>
  )
}
```

### 6.5 Analytics Page — `frontend/app/analytics/page.tsx`

```tsx
// frontend/app/analytics/page.tsx
import { AnalyticsTab } from '@/components/analytics-tab'

export default function AnalyticsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white">
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-5 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              📊 Analytics — 参与度排行榜
            </h1>
            <p className="text-indigo-300 text-sm mt-1">
              按真实用户互动数据重新排名的商机评分（每小时自动更新）
            </p>
          </div>
          <a href="/opportunities" className="text-sm text-indigo-300 hover:text-white transition-colors">
            ← 商机列表
          </a>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* Score formula explanation */}
        <div className="bg-white/5 border border-white/10 rounded-xl px-5 py-4 mb-8 text-sm text-white/60">
          <span className="text-white font-semibold mr-2">📐 综合评分公式:</span>
          <code className="text-emerald-400 font-mono">
            composite = roi_score × 0.6 + engagement_score × 0.4
          </code>
          <span className="ml-3">
            参与度 = views×40% + plays×30% + downloads×20% + test_completes×10%
          </span>
        </div>

        <AnalyticsTab />
      </div>
    </div>
  )
}
```

### 6.6 Event Logging Hook — `frontend/lib/useEngagement.ts` (NEW)

```typescript
// frontend/lib/useEngagement.ts
'use client'

import { useCallback, useRef } from 'react'
import { analyticsApi } from '@/lib/api'

/**
 * Returns a stable `trackEvent` function that fires engagement events
 * without re-rendering the calling component.
 *
 * Usage:
 *   const { trackEvent } = useEngagement()
 *   <button onClick={() => trackEvent(productId, 'view')}>View</button>
 */
export function useEngagement() {
  // session_id: stable per-browser-tab UUID (not PII)
  const sessionRef = useRef<string>(
    typeof window !== 'undefined'
      ? (localStorage.getItem('_nt_sid') ?? (() => {
          const id = crypto.randomUUID()
          localStorage.setItem('_nt_sid', id)
          return id
        })())
      : '',
  )

  const trackEvent = useCallback(
    (
      productId: string,
      eventType: 'view' | 'audio_play' | 'ebook_download' | 'test_complete',
      metadata?: Record<string, unknown>,
    ) => {
      void analyticsApi.logEvent(productId, eventType, sessionRef.current, metadata)
    },
    [],
  )

  return { trackEvent }
}
```

### 6.7 Instrument Existing Product Pages

**`frontend/app/opportunities/[id]/products/[product_id]/page.tsx`** — ADD auto view tracking:

```typescript
// At top of component, add:
import { useEngagement } from '@/lib/useEngagement'
import { useEffect } from 'react'

// Inside component body:
const { trackEvent } = useEngagement()
useEffect(() => {
  if (product?.id) {
    trackEvent(product.id, 'view', { referrer: document.referrer })
  }
}, [product?.id])

// On audio play button click, add:
trackEvent(product.id, 'audio_play', { script_id: scriptId })

// On ebook download button click, add:
trackEvent(product.id, 'ebook_download', { format: 'pdf' })

// On test completion callback, add:
trackEvent(product.id, 'test_complete', { result_type: resultType })
```

### 6.8 Navigation — Patch `frontend/app/opportunities/page.tsx`

Add an "Analytics" button to the header:
```tsx
{/* ADD next to the ← 返回主页 link */}
<a
  href="/analytics"
  className="text-sm text-amber-400 hover:text-white transition-colors font-medium"
>
  📊 Analytics
</a>
```

---

## 7. Database Migration

Since this project uses SQLAlchemy with `Base.metadata.create_all` on startup (no Alembic migrations currently), new tables will be **auto-created** at server startup. However, back-references added to existing models (TrendSignal, OpportunityReport) are relationship-only and require **no schema changes**.

For JSONB column (vs plain JSON), either:
- Use `JSON` column type (cross-DB compatible) if no JSONB operators needed  
- Or install `psycopg2-binary` and use `from sqlalchemy.dialects.postgresql import JSONB`

**Recommendation:** Use `JSONB` for `ProductEngagement.metadata` for future GIN index support. Keep `JSON` for `OpportunityScore` fields.

> **IMPORTANT:** If running in production with an existing DB, add an Alembic migration:
```bash
cd ~/autonomous-ai-factory/backend
alembic revision --autogenerate -m "phase5a_engagement_scoring"
alembic upgrade head
```

---

## 8. Configuration & Environment

### 8.1 New Environment Variables

Add to `.env.example`:
```env
# Phase 5-A — Feedback Loop
ENGAGEMENT_REGEN_THRESHOLD=50   # auto-regen trigger view count
SCORE_NORMALIZATION_VIEWS=500   # view count that saturates engagement at 10
SCORE_NORMALIZATION_PLAYS=200
SCORE_NORMALIZATION_DOWNLOADS=100
SCORE_NORMALIZATION_TESTS=150
```

Update `backend/workers/score_worker.py` to read from env:
```python
import os
REGEN_THRESHOLD = int(os.getenv("ENGAGEMENT_REGEN_THRESHOLD", "50"))
SATURATION_VIEWS = int(os.getenv("SCORE_NORMALIZATION_VIEWS", "500"))
```

---

## 9. Implementation Order (Suggested Sprint)

| Step | File | Effort | Depends On |
|---|---|---|---|
| 1 | `backend/models/engagement.py` | 30 min | — |
| 2 | Patch `backend/models/trend.py` (back-refs) | 10 min | Step 1 |
| 3 | Patch `backend/models/__init__.py` | 5 min | Step 1 |
| 4 | `backend/api/analytics.py` | 45 min | Steps 1–3 |
| 5 | Patch `backend/main.py` | 5 min | Step 4 |
| 6 | `backend/workers/score_worker.py` | 60 min | Steps 1–3 |
| 7 | Patch `backend/workers/pipeline.py` | 10 min | Step 6 |
| 8 | `frontend/types/neurotrend.ts` extensions | 10 min | — |
| 9 | `frontend/lib/api.ts` extensions | 15 min | Step 8 |
| 10 | `frontend/lib/useEngagement.ts` | 15 min | Step 9 |
| 11 | `frontend/components/engagement-bar.tsx` | 20 min | — |
| 12 | `frontend/components/analytics-tab.tsx` | 45 min | Steps 8–11 |
| 13 | `frontend/app/analytics/page.tsx` | 15 min | Step 12 |
| 14 | Instrument existing product pages | 30 min | Step 10 |
| 15 | Patch `frontend/app/opportunities/page.tsx` nav | 10 min | Step 13 |

**Total estimated effort: ~5.5 hours**

---

## 10. Testing Notes

### Backend Unit Tests

Create `backend/tests/test_analytics.py`:
```python
# Test log_event endpoint
# Test get_top_opportunities with zero data (empty list)
# Test get_product_stats for unknown product (404)
# Test recalculate_scores() with mock DB data
#   - verify composite_score formula: roi*0.6 + eng*0.4
#   - verify normalization ceiling saturation
#   - verify regen not triggered below threshold
#   - verify regen triggered above threshold
```

### Frontend Tests

Create `frontend/__tests__/analytics-tab.test.tsx`:
```typescript
// Test AnalyticsTab renders loading state
// Test AnalyticsTab renders empty state
// Test AnalyticsTab renders items with correct scores
// Test useEngagement fires event without throwing
// Test event type mapping to API call
```

---

## 11. Key Design Decisions & Notes

1. **Fire-and-forget tracking**: `POST /events` always returns 201 even for unknown product IDs; the frontend hook silently swallows errors. This ensures tracking never blocks UI.

2. **UPSERT strategy**: `OpportunityScore` uses PostgreSQL `ON CONFLICT DO UPDATE` — safe to run recalculate_scores idempotently.

3. **Scoring formula**:
   ```
   engagement_score = normalize(views)*0.40 + normalize(plays)*0.30
                    + normalize(downloads)*0.20 + normalize(tests)*0.10
   composite_score  = roi_score * 0.6 + engagement_score * 0.4
   ```
   This ensures original AI analysis (ROI) still dominates (60%) while real user signal lifts scores.

4. **Normalization**: Soft ceiling approach (`min(10, value/ceiling * 10)`) prevents viral outliers from completely dominating. Ceilings are env-configurable.

5. **Regen guard**: Before auto-triggering a new product generation, the worker checks that no product for that opportunity is currently in `pending` or `generating` state. This prevents runaway job storms.

6. **Session IDs**: Anonymous `crypto.randomUUID()` stored in `localStorage` as `_nt_sid`. No PII, purely for deduplication analysis. Not enforced server-side.

7. **ARQ cron import**: Requires `arq >= 0.25`. Check with `pip show arq`. The cron syntax is `arq.cron(func, minute=0)` which fires at the top of each hour.

8. **JSONB vs JSON**: `ProductEngagement.metadata` uses JSONB for future filtering (e.g., `WHERE metadata->>'result_type' = 'INFJ'`). `OpportunityScore` uses plain floats only.

---

## 12. Future Extensions (Phase 5-B)

- **Redis caching**: Cache `get_top_opportunities` result in Redis for 5 minutes to avoid DB aggregation on every page load.
- **Real-time counters**: Use Redis `INCR` for live view counts, batch-flush to PostgreSQL every 5 minutes.
- **Cohort analysis**: Add `created_at` range filter to `top-opportunities` endpoint.
- **A/B testing**: Add `variant` field to `ProductEngagement.metadata` to compare content versions.
- **Webhook**: After regen completes, send Lark/DingTalk notification via existing `core/notifier.py`.
- **GIN index**: Once engagement data grows, add `CREATE INDEX ON product_engagements USING GIN (metadata)` for metadata queries.
