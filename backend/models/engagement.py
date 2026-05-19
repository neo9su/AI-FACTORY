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
    opportunity_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("opportunity_reports.id", ondelete="SET NULL"),
        nullable=True,
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
    event_metadata: Mapped[Optional[dict]] = mapped_column(
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
        unique=True,  # one row per opportunity, upserted
        index=True,
    )
    # raw engagement numbers (sum across all products of this opportunity)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_plays: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_downloads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_test_completes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    engagement_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        # normalized 0–10, computed in score_worker
    )
    engagement_boost: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        # = engagement_score × 0.4 (the additive boost component)
    )
    composite_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        index=True,
        # = original roi_score × 0.6 + engagement_score × 0.4
    )

    # relationships
    opportunity: Mapped["OpportunityReport"] = relationship(  # noqa: F821
        "OpportunityReport",
        back_populates="score",
        lazy="raise",
    )
