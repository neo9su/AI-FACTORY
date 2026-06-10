"""Video production pipeline models.

Tracks video projects through the content production pipeline:
去水印 → 配音 → 换脸 → 唇形同步 → 去重处理 → 发布
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin


class VideoProjectStatus(str):
    """Status values for a video production project."""

    CREATED = "created"
    PIPELINE_RUNNING = "pipeline_running"
    PIPELINE_COMPLETED = "pipeline_completed"
    PUBLISHED = "published"
    FAILED = "failed"


class StageStatus(str):
    """Status values for an individual pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


VIDEO_PIPELINE_STAGES = [
    "remove_watermark",   # 去水印
    "dub",                # 配音
    "face_swap",          # 换脸
    "lip_sync",           # 唇形同步
    "dedup",              # 去重处理
    "overlay_stickers",   # 叠加动态贴纸+新字幕样式
]

STAGE_DISPLAY_NAMES = {
    "remove_watermark": "去水印",
    "dub": "配音",
    "face_swap": "换脸",
    "lip_sync": "唇形同步",
    "dedup": "去重处理",
    "overlay_stickers": "叠加贴纸+字幕",
}


class VideoProject(Base, UUIDMixin, TimestampMixin):
    """A video production project with full pipeline tracking."""

    __tablename__ = "video_projects"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=VideoProjectStatus.CREATED
    )

    # Source video info
    source_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_filepath: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_resolution: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Pipeline progress tracking
    current_stage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_stages: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    # Error tracking
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Publishing
    publish_platform: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    stages: Mapped[list[VideoPipelineStage]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="VideoPipelineStage.stage_order",
    )
    assets: Mapped[list[VideoAsset]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<VideoProject(id={self.id}, title={self.title!r}, status={self.status})>"


class VideoPipelineStage(Base, UUIDMixin, TimestampMixin):
    """Individual stage in a video project pipeline."""

    __tablename__ = "video_pipeline_stages"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=StageStatus.PENDING
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)

    # Parameters for this stage (JSON)
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Execution metadata
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Result — reference to output asset
    output_asset_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("video_assets.id"), nullable=True
    )

    # Relationships
    project: Mapped[VideoProject] = relationship(back_populates="stages")
    output_asset: Mapped[Optional[VideoAsset]] = relationship(
        foreign_keys=[output_asset_id],
        post_update=True,
    )

    def __repr__(self) -> str:
        return f"<Stage(project={self.project_id}, name={self.stage_name}, status={self.status})>"


class VideoAsset(Base, UUIDMixin, TimestampMixin):
    """A video file asset generated during the pipeline."""

    __tablename__ = "video_assets"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    md5_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Asset type
    asset_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="output"
    )  # source, intermediate, output, publish_ready

    # Which stage produced this asset
    source_stage: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    project: Mapped[VideoProject] = relationship(back_populates="assets")

    def __repr__(self) -> str:
        return f"<VideoAsset(id={self.id}, name={self.filename!r}, type={self.asset_type})>"
