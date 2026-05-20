"""Phase 5D — Platform session / cookie storage."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class PlatformSession(UUIDMixin, TimestampMixin, Base):
    """Stores browser cookies for a platform login session."""

    __tablename__ = "platform_sessions"

    platform: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
        # "xiaohongshu" | "douyin"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
        # pending | scanning | logged_in | expired | failed
    )
    cookies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # List of cookie dicts: [{name, value, domain, path, expires, ...}]

    user_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Scraped user info after login: {nickname, user_id, avatar_url}

    qr_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Path to QR code screenshot: /static/qr/<session_id>.png

    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
