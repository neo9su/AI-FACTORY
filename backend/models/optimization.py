"""Phase 5-C — 持续优化闭环数据模型."""
from __future__ import annotations
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, UUIDMixin, TimestampMixin


class ContentPerformance(Base, UUIDMixin, TimestampMixin):
    """每个产品的表现分析快照 — 被 optimizer_worker 周期性写入。"""

    __tablename__ = "content_performances"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("content_products.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_reports.id", ondelete="SET NULL"), index=True
    )

    # ── 原始聚合数据 ──
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_plays: Mapped[int] = mapped_column(Integer, default=0)
    total_downloads: Mapped[int] = mapped_column(Integer, default=0)
    total_test_completes: Mapped[int] = mapped_column(Integer, default=0)

    # ── 行为指标（0~10 标准化） ──
    hook_retention_rate: Mapped[float] = mapped_column(Float, default=0.0)
    angle_click_rate: Mapped[float] = mapped_column(Float, default=0.0)
    format_completion_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # ── 衍生指标 ──
    engagement_efficiency: Mapped[float] = mapped_column(Float, default=0.0)
    audience_match_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ── 结论 ──
    recommendation: Mapped[str | None] = mapped_column(Text)
    performance_grade: Mapped[str] = mapped_column(String(8), default="C")  # S/A/B/C/D


class ContentPattern(Base, UUIDMixin, TimestampMixin):
    """系统发现的有效模式库 — 跨产品聚合的通用经验。"""

    __tablename__ = "content_patterns"

    pattern_type: Mapped[str] = mapped_column(String(32), index=True)  # hook / angle / format / timing
    pattern_key: Mapped[str] = mapped_column(String(128))  # 模式标识
    pattern_value: Mapped[str] = mapped_column(Text)  # 具体内容

    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0~10
    sample_count: Mapped[int] = mapped_column(Integer, default=0)  # 验证次数
    emotion_tags: Mapped[list | None] = mapped_column(JSON)  # 关联情绪标签

    __table_args__ = (Index("ix_cp_type_key", "pattern_type", "pattern_key"),)


class ABTest(Base, UUIDMixin, TimestampMixin):
    """A/B 测试记录。"""

    __tablename__ = "ab_tests"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("content_products.id", ondelete="CASCADE"), index=True
    )
    variants_count: Mapped[int] = mapped_column(Integer, default=2)
    variants: Mapped[dict] = mapped_column(JSON, default=dict)
    platform: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="running")  # running / completed / failed
    duration_hours: Mapped[int] = mapped_column(Integer, default=168)

    # ── 结果 ──
    engagement_by_variant: Mapped[dict] = mapped_column(JSON, default=dict)
    winner_id: Mapped[str | None] = mapped_column(String(64))
    confidence_score: Mapped[float | None] = mapped_column(Float)

    # ── 反馈 ──
    insight_summary: Mapped[str | None] = mapped_column(Text)
    applied_to_factory: Mapped[bool] = mapped_column(Boolean, default=False)
