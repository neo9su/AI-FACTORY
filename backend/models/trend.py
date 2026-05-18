"""SQLAlchemy ORM models for NeuroTrend — trend signals, opportunity reports, content products."""
from typing import Optional

from sqlalchemy import JSON, Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Relationships
    trend_signal: Mapped[Optional["TrendSignal"]] = relationship(
        "TrendSignal", back_populates="opportunity_reports"
    )
    products: Mapped[list["ContentProduct"]] = relationship(
        "ContentProduct", back_populates="opportunity", cascade="all, delete-orphan"
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

    # Relationships
    opportunity: Mapped["OpportunityReport"] = relationship(
        "OpportunityReport", back_populates="products"
    )
