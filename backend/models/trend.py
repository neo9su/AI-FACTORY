"""SQLAlchemy ORM models for NeuroTrend — trend signals, opportunity reports, content products."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

# TYPE_CHECKING imports avoided — string-based forward refs used instead

from backend.models.base import Base, TimestampMixin, UUIDMixin


class TrendSignal(UUIDMixin, TimestampMixin, Base):
    """Represents a single hot-topic signal collected from external sources."""

    __tablename__ = "trend_signals"

    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    viral_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    emotion_tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    pain_points: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Relationships
    opportunity_reports: Mapped[list["OpportunityReport"]] = relationship(
        "OpportunityReport", back_populates="trend_signal", cascade="all, delete-orphan"
    )


class OpportunityReport(UUIDMixin, TimestampMixin, Base):
    """AI-generated opportunity analysis report derived from a trend signal."""

    __tablename__ = "opportunity_reports"

    trend_signal_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("trend_signals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    why_viral: Mapped[str] = mapped_column(Text, nullable=False)
    core_emotions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    core_pain_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    willingness_to_pay: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    product_suggestions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    best_product: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    roi_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    automation_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    seo_value: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lifecycle: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hook_lines: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # 营销文案钩子
    content_angles: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # 内容切入角度
    monetization_strategy: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 变现策略
    action_plan: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 行动计划
    audience_profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 受众画像

    # Relationships
    trend_signal: Mapped[Optional["TrendSignal"]] = relationship(
        "TrendSignal", back_populates="opportunity_reports"
    )
    products: Mapped[list["ContentProduct"]] = relationship(
        "ContentProduct", back_populates="opportunity", cascade="all, delete-orphan"
    )
    score: Mapped[Optional["OpportunityScore"]] = relationship(
        "OpportunityScore",
        back_populates="opportunity",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ContentProduct(UUIDMixin, TimestampMixin, Base):
    """A generated content product (ebook, test, video, etc.) linked to an opportunity."""

    __tablename__ = "content_products"

    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("opportunity_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    content_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # TTS 配音状态
    tts_status: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # None/pending/generating/ready/failed
    tts_audio_urls: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # [{script_id: 1, url: "/static/audio/xxx.wav", duration_hint: "45s"}]
    tts_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    opportunity: Mapped["OpportunityReport"] = relationship(
        "OpportunityReport", back_populates="products"
    )
    engagements: Mapped[list["ProductEngagement"]] = relationship(
        "ProductEngagement", back_populates="product", cascade="all, delete-orphan"
    )


class TrendScanJob(UUIDMixin, TimestampMixin, Base):
    """跟踪异步趋势扫描任务状态"""

    __tablename__ = "trend_scan_jobs"

    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)  # queued|running|done|failed
    sources: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scanned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunities_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
