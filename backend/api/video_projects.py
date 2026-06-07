"""Video production pipeline API routes.

Manages video projects through the content production pipeline:
去水印 → 配音 → 换脸 → 唇形同步 → 去重处理 → 发布
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.session import get_db
from backend.models.video import (
    VIDEO_PIPELINE_STAGES,
    STAGE_DISPLAY_NAMES,
    VideoAsset,
    VideoPipelineStage,
    VideoProject,
    VideoProjectStatus,
    StageStatus,
)

router = APIRouter()

# Directory for uploaded/source videos
VIDEO_STORAGE = Path.home() / "autonomous-ai-factory" / "videos"
VIDEO_STORAGE.mkdir(parents=True, exist_ok=True)


# ─── Pydantic Schemas ────────────────────────────────────────────────────────


class VideoProjectCreate(BaseModel):
    """Schema for creating a new video project."""

    title: str
    description: Optional[str] = None
    source_filepath: Optional[str] = None  # Path to already-uploaded source


class VideoProjectResponse(BaseModel):
    """Schema for video project response."""

    id: str
    title: str
    description: Optional[str]
    status: str
    source_filename: Optional[str]
    source_filepath: Optional[str]
    source_duration: Optional[float]
    source_resolution: Optional[str]
    current_stage: Optional[int]
    total_stages: int
    error_log: Optional[str]
    publish_platform: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoProjectDetailResponse(VideoProjectResponse):
    """Detailed response with stages and assets."""

    stages: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []


class VideoPipelineStageResponse(BaseModel):
    """Schema for pipeline stage response."""

    id: str
    stage_name: str
    stage_order: int
    status: str
    display_name: str
    params: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    error_log: Optional[str]
    output_asset: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class VideoAssetResponse(BaseModel):
    """Schema for video asset response."""

    id: str
    filename: str
    filepath: str
    file_size_bytes: Optional[int]
    duration_seconds: Optional[float]
    resolution: Optional[str]
    md5_hash: Optional[str]
    asset_type: str
    source_stage: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StageRunResponse(BaseModel):
    """Response after triggering a stage run."""

    message: str
    stage: str
    status: str


# ─── Helper Functions ────────────────────────────────────────────────────────


def _project_to_detail(project: VideoProject) -> dict[str, Any]:
    """Convert project ORM to detail dict with stages and assets."""
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "status": project.status,
        "source_filename": project.source_filename,
        "source_filepath": project.source_filepath,
        "source_duration": project.source_duration,
        "source_resolution": project.source_resolution,
        "current_stage": project.current_stage,
        "total_stages": project.total_stages,
        "error_log": project.error_log,
        "publish_platform": project.publish_platform,
        "published_at": project.published_at,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "stages": [
            {
                "id": s.id,
                "stage_name": s.stage_name,
                "stage_order": s.stage_order,
                "status": s.status,
                "display_name": s.display_name,
                "params": s.params,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
                "duration_seconds": s.duration_seconds,
                "error_log": s.error_log,
                "output_asset": {
                    "id": s.output_asset.id,
                    "filename": s.output_asset.filename,
                    "filepath": s.output_asset.filepath,
                    "file_size_bytes": s.output_asset.file_size_bytes,
                    "duration_seconds": s.output_asset.duration_seconds,
                    "resolution": s.output_asset.resolution,
                    "md5_hash": s.output_asset.md5_hash,
                    "asset_type": s.output_asset.asset_type,
                    "source_stage": s.output_asset.source_stage,
                    "created_at": s.output_asset.created_at,
                } if s.output_asset else None,
            }
            for s in project.stages
        ],
        "assets": [
            {
                "id": a.id,
                "filename": a.filename,
                "filepath": a.filepath,
                "file_size_bytes": a.file_size_bytes,
                "duration_seconds": a.duration_seconds,
                "resolution": a.resolution,
                "md5_hash": a.md5_hash,
                "asset_type": a.asset_type,
                "source_stage": a.source_stage,
                "created_at": a.created_at,
            }
            for a in project.assets
        ],
    }


async def _init_stages(project: VideoProject, db: AsyncSession) -> None:
    """Create default pipeline stages for a new project."""
    for order, stage_name in enumerate(VIDEO_PIPELINE_STAGES):
        stage = VideoPipelineStage(
            id=str(uuid4()),
            project_id=project.id,
            stage_name=stage_name,
            stage_order=order,
            status=StageStatus.PENDING,
            display_name=STAGE_DISPLAY_NAMES.get(stage_name, stage_name),
        )
        db.add(stage)
    project.total_stages = len(VIDEO_PIPELINE_STAGES)
    await db.commit()
    await db.refresh(project)


# ─── API Routes ──────────────────────────────────────────────────────────────


@router.post("/video-projects", response_model=VideoProjectResponse)
async def create_video_project(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    source: Optional[UploadFile] = File(None),
    source_filepath: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> VideoProject:
    """Create a new video production project.

    Upload a source video or provide a file path.
    Initializes the 5-stage pipeline automatically.
    """
    project = VideoProject(
        id=str(uuid4()),
        title=title,
        description=description,
        status=VideoProjectStatus.CREATED,
        current_stage=None,
        total_stages=len(VIDEO_PIPELINE_STAGES),
    )

    # Handle upload
    if source:
        # Save uploaded file
        ext = os.path.splitext(source.filename or "video.mp4")[1] or ".mp4"
        filename = f"{project.id}_source{ext}"
        filepath = str(VIDEO_STORAGE / filename)
        content = await source.read()
        with open(filepath, "wb") as f:
            f.write(content)

        project.source_filename = source.filename
        project.source_filepath = filepath

        # Create source asset
        asset = VideoAsset(
            id=str(uuid4()),
            project_id=project.id,
            filename=source.filename or "source.mp4",
            filepath=filepath,
            file_size_bytes=len(content),
            asset_type="source",
        )
        db.add(asset)
    elif source_filepath:
        project.source_filename = os.path.basename(source_filepath)
        project.source_filepath = source_filepath

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Initialize pipeline stages
    await _init_stages(project, db)

    return project


@router.get("/video-projects", response_model=list[VideoProjectResponse])
async def list_video_projects(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[VideoProject]:
    """List all video production projects.

    Args:
        status: Optional filter by project status
        limit: Max results per page
        offset: Pagination offset
    """
    query = select(VideoProject).order_by(VideoProject.created_at.desc())

    if status:
        query = query.where(VideoProject.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/video-projects/{project_id}", response_model=VideoProjectDetailResponse)
async def get_video_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get detailed video project info with stages and assets."""
    result = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id)
        .options(
            selectinload(VideoProject.stages).selectinload(VideoPipelineStage.output_asset),
            selectinload(VideoProject.assets),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    return _project_to_detail(project)


@router.get("/video-projects/{project_id}/assets", response_model=list[VideoAssetResponse])
async def list_video_assets(
    project_id: str,
    asset_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> list[VideoAsset]:
    """List all assets for a video project."""
    query = select(VideoAsset).where(
        VideoAsset.project_id == project_id
    ).order_by(VideoAsset.created_at.desc())

    if asset_type:
        query = query.where(VideoAsset.asset_type == asset_type)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/video-projects/{project_id}/run-stage/{stage_name}", response_model=StageRunResponse)
async def run_pipeline_stage(
    project_id: str,
    stage_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Trigger execution of a specific pipeline stage.

    Args:
        project_id: Video project ID
        stage_name: One of: remove_watermark, dub, face_swap, lip_sync, dedup

    Returns:
        StageRunResponse: Execution status
    """
    # Validate stage name
    if stage_name not in VIDEO_PIPELINE_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {stage_name}. Valid: {', '.join(VIDEO_PIPELINE_STAGES)}",
        )

    # Load project with stages
    result = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id)
        .options(selectinload(VideoProject.stages))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    # Find the stage
    stage = next((s for s in project.stages if s.stage_name == stage_name), None)
    if not stage:
        raise HTTPException(status_code=404, detail=f"Stage '{stage_name}' not found")

    # Mark as running
    stage.status = StageStatus.RUNNING
    stage.started_at = datetime.utcnow()
    project.status = VideoProjectStatus.PIPELINE_RUNNING
    project.current_stage = stage.stage_order
    project.error_log = None
    await db.commit()

    # TODO: Dispatch to actual worker/executor
    # For now, we mark it as a placeholder execution
    # The actual ffmpeg/ComfyUI subprocess execution will be added in a future phase
    stage.status = StageStatus.PENDING  # Reset so UI shows it's queued
    stage.started_at = None
    await db.commit()

    return {
        "message": f"Stage '{stage_name}' queued for execution",
        "stage": stage_name,
        "status": "queued",
    }


@router.post("/video-projects/{project_id}/start-pipeline")
async def start_full_pipeline(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start the full pipeline execution from stage 0.

    Resets all stages and begins sequential execution.
    """
    result = await db.execute(
        select(VideoProject)
        .where(VideoProject.id == project_id)
        .options(selectinload(VideoProject.stages))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    # Reset all stages
    for stage in project.stages:
        stage.status = StageStatus.PENDING
        stage.started_at = None
        stage.completed_at = None
        stage.duration_seconds = None
        stage.error_log = None

    project.status = VideoProjectStatus.CREATED
    project.current_stage = 0
    project.error_log = None
    await db.commit()

    return {
        "message": f"Pipeline reset and ready. Starting from stage 0: {STAGE_DISPLAY_NAMES.get(VIDEO_PIPELINE_STAGES[0], VIDEO_PIPELINE_STAGES[0])}",
        "project_id": project_id,
        "status": "ready",
    }


@router.delete("/video-projects/{project_id}")
async def delete_video_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a video project and all its assets."""
    result = await db.execute(
        select(VideoProject).where(VideoProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Video project not found")

    # Delete source files
    if project.source_filepath and os.path.exists(project.source_filepath):
        os.remove(project.source_filepath)

    await db.delete(project)
    await db.commit()

    return {"message": f"Video project '{project.title}' deleted", "status": "deleted"}
