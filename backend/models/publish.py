from __future__ import annotations

from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin

class PublishTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "publish_tasks"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("content_products.id", ondelete="CASCADE"), 
        index=True
    )
    platform: Mapped[str] = mapped_column(String(3_0))  # 'xiaohongshu', 'douyin'
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, generating, ready, published, failed
    
    # The actual prepared content (text, hashtags, image_prompts, etc.)
    publish_package: Mapped[dict] = mapped_column(JSON, default=dict)
    
    error_log: Mapped[str | None] = mapped_column(Text)
    
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    product: Mapped["ContentProduct"] = relationship("ContentProduct", back_populates="publish_tasks")

    def __repr__(self) -> str:
        return f"<PublishTask(id={self.id}, platform={self.platform}, status={self.status})>"
