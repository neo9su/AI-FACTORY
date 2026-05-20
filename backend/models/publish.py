"""Phase 5-B — Publish job tracking model."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


class PublishJob(UUIDMixin, TimestampMixin, Base):
    """Tracks a publish attempt for a ContentProduct to a specific platform."""

    __tablename__ = "publish_jobs"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("content_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
        # allowed: "douyin" | "xiaohongshu" | "tiktok"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
        # pending | packaging | ready | published | failed
    )
    bundle_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # e.g. "/static/publish/<product_id>/douyin/bundle.json"

    bundle_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # full publish bundle: title, caption, hashtags, audio_url, cover_url, script_text

    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship back to product
    product: Mapped["ContentProduct"] = relationship(  # noqa: F821
        "ContentProduct",
        back_populates="publish_jobs",
    )
