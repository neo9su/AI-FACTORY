"""Video production pipeline API routes.

Manages video projects through the content production pipeline:
去水印 → 配音 → 换脸 → 唇形同步 → 去重处理 → 发布
"""
from __future__ import annotations

import logging

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



class WatermarkWaypoint(BaseModel):
    """Single waypoint in a watermark trajectory."""
    t: float
    x: int
    y: int

class WatermarkSegment(BaseModel):
    """A time segment with trajectory waypoints."""
    start: float
    end: float
    waypoints: list[WatermarkWaypoint] = []
    w: int = 100
    h: int = 30
    subtitle_safe: bool = False

class WatermarkConfig(BaseModel):
    """Configuration for watermark removal stage."""
    watermark_name: str = ""
    watermark_type: str = "text"
    movement_type: str = "moving"
    trajectory_description: str = ""
    subtitle_zone: dict = {"y1": 710, "y2": 745}
    segments: list[WatermarkSegment] = []
    analysis_status: str = "not_started"
    analysis_result: str = ""

class DedupConfigModel(BaseModel):
    """Configuration for dedup stage."""
    dedup_name: str = "去重处理"
    color_temp: float = 0.02
    saturation: float = 1.05
    brightness: float = 0.02
    contrast: float = 1.02
    speed_variation: float = 0.02
    pixel_shift: int = 1
    noise_level: float = 0.001
    dither: bool = True
    bgm_replace: bool = False
    bgm_volume: float = 0.3
    bgm_source: Optional[str] = None
    strip_metadata: bool = True
    preset: str = "fast"
    crf: int = 23



@router.put("/video-projects/{project_id}/stage-config/remove_watermark")
async def update_watermark_config(
    project_id: str,
    config: WatermarkConfig,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Save watermark removal configuration for a project."""
    result = await db.execute(
        select(VideoPipelineStage)
        .where(
            VideoPipelineStage.project_id == project_id,
            VideoPipelineStage.stage_name == "remove_watermark",
        )
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(404, "remove_watermark stage not found")

    existing = stage.params or {}
    existing.update(config.model_dump())
    stage.params = existing
    await db.commit()
    return {
        "message": "Watermark config saved",
        "watermark_name": config.watermark_name,
        "movement_type": config.movement_type,
        "segments": len(config.segments),
    }


@router.get("/video-projects/{project_id}/stage-config/remove_watermark")
async def get_watermark_config(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get current watermark removal configuration."""
    result = await db.execute(
        select(VideoPipelineStage)
        .where(
            VideoPipelineStage.project_id == project_id,
            VideoPipelineStage.stage_name == "remove_watermark",
        )
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(404, "remove_watermark stage not found")
    return {
        "project_id": project_id,
        "params": stage.params or {},
        "status": stage.status,
    }


@router.put("/video-projects/{project_id}/stage-config/dedup")
async def update_dedup_config(
    project_id: str,
    config: DedupConfigModel,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Save dedup configuration for a project."""
    result = await db.execute(
        select(VideoPipelineStage)
        .where(
            VideoPipelineStage.project_id == project_id,
            VideoPipelineStage.stage_name == "dedup",
        )
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(404, "dedup stage not found")

    existing = stage.params or {}
    existing.update(config.model_dump())
    stage.params = existing
    await db.commit()
    return {
        "message": "Dedup config saved",
        "dedup_name": config.dedup_name,
        "saturation": config.saturation,
        "noise_level": config.noise_level,
    }


@router.get("/video-projects/{project_id}/stage-config/dedup")
async def get_dedup_config(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get current dedup configuration."""
    result = await db.execute(
        select(VideoPipelineStage)
        .where(
            VideoPipelineStage.project_id == project_id,
            VideoPipelineStage.stage_name == "dedup",
        )
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise HTTPException(404, "dedup stage not found")
    return {
        "project_id": project_id,
        "params": stage.params or {},
        "status": stage.status,
    }

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

    # Execute stage
    if stage_name == "remove_watermark":
        from backend.core.video_effects.moving_watermark_remover import process_video
        # Input: source file or latest asset
        result = await db.execute(
            select(VideoAsset)
            .where(VideoAsset.project_id == project_id)
            .order_by(VideoAsset.created_at.desc())
        )
        last_asset = result.scalars().first()
        input_video = last_asset.filepath if last_asset else project.source_filepath or ""

        if not input_video or not os.path.exists(input_video):
            raise HTTPException(400, "No input video available for watermark removal")

        output_video = str(Path(input_video).with_name(
            Path(input_video).stem + "_clean" + Path(input_video).suffix
        ))

        # Use stage params as config (set via detect-watermark API)
        config = stage.params or {}
        if isinstance(config, str):
            config = json.loads(config)

        logging.getLogger(__name__).info(
            "Starting remove_watermark with config: name=%s segments=%d",
            config.get("watermark_name", "?"), len(config.get("segments", []))
        )

        res = process_video(
            input_path=input_video,
            output_path=output_video,
            config=config,
        )

        if res.get("success"):
            stage.status = StageStatus.COMPLETED
            stage.output_filepath = output_video
            stage.output_url = output_video
            stage.duration_seconds = float(res.get("duration_seconds", 0))
            asset = VideoAsset(
                project_id=project_id,
                filename=Path(output_video).name,
                filepath=output_video,
                asset_type="output",
                source_stage="remove_watermark",
                duration_seconds=float(res.get("duration_seconds", 0)),
            )
            db.add(asset)
            project.source_filepath = output_video
        else:
            stage.status = StageStatus.FAILED
            stage.error_log = res.get("error", "Unknown error")

    elif stage_name == "overlay_stickers":
        from backend.core.video_effects.overlay import apply_overlay_effects, SubtitleStyle
        # Get latest video asset from previous stage
        result = await db.execute(
            select(VideoAsset)
            .where(VideoAsset.project_id == project_id)
            .order_by(VideoAsset.created_at.desc())
        )
        last_asset = result.scalars().first()
        input_video = last_asset.filepath if last_asset else project.source_filepath or ""

        if not input_video or not os.path.exists(input_video):
            raise HTTPException(400, "No input video available for overlay stage")

        output_video = str(Path(input_video).with_name(
            Path(input_video).stem + "_with_stickers" + Path(input_video).suffix
        ))

        style = SubtitleStyle(
            font="SmileySans-Oblique",
            font_size=24,
            font_color="white",
            font_outline=2,
            font_outline_color="black",
            position="top_right",
            margin_x=40,
            margin_y=40,
            highlight_color="yellow",
            highlight_min_chars=4,
            use_background=True,
        )

        res = apply_overlay_effects(
            input_video=input_video,
            output_video=output_video,
            style=style,
        )

        if res.get("success"):
            stage.status = StageStatus.COMPLETED
            stage.output_filepath = output_video
            stage.output_url = output_video
            stage.duration_seconds = float(res.get("duration", 0))
            # Create asset record
            asset = VideoAsset(
                project_id=project_id,
                filename=Path(output_video).name,
                filepath=output_video,
                asset_type="output",
                source_stage="overlay_stickers",
                duration_seconds=float(res.get("duration", 0)),
            )
            db.add(asset)
            # Update project source to latest output
            project.source_filepath = output_video
        else:
            stage.status = StageStatus.FAILED
            stage.error_log = res.get("error", "Unknown error")

    elif stage_name == "dedup":
        from backend.core.video_effects.dedup import apply_dedup_effects, DedupConfig
        # Get latest video asset from previous stage
        result = await db.execute(
            select(VideoAsset)
            .where(VideoAsset.project_id == project_id)
            .order_by(VideoAsset.created_at.desc())
        )
        last_asset = result.scalars().first()
        input_video = last_asset.filepath if last_asset else project.source_filepath or ""

        if not input_video or not os.path.exists(input_video):
            raise HTTPException(400, "No input video available for dedup stage")

        output_video = str(Path(input_video).with_name(
            Path(input_video).stem + "_dedup" + Path(input_video).suffix
        ))

        # Read config from stage.params (set via PUT stage-config/dedup)
        params = stage.params or {}
        if isinstance(params, str):
            params = json.loads(params)
        config = DedupConfig.from_dict(params)
        logging.getLogger(__name__).info(
            "Starting dedup with config: name=%s speed=%.3f noise=%.4f",
            config.dedup_name, config.speed_variation, config.noise_level,
        )

        res = apply_dedup_effects(
            input_video=input_video,
            output_video=output_video,
            config=config,
        )

        if res.get("success"):
            stage.status = StageStatus.COMPLETED
            stage.output_filepath = output_video
            stage.output_url = output_video
            stage.duration_seconds = float(res.get("duration", 0))
            asset = VideoAsset(
                project_id=project_id,
                filename=Path(output_video).name,
                filepath=output_video,
                asset_type="output",
                source_stage="dedup",
                duration_seconds=float(res.get("duration", 0)),
            )
            db.add(asset)
            project.source_filepath = output_video
        else:
            stage.status = StageStatus.FAILED
            stage.error_log = res.get("error", "Unknown error")

    elif stage_name == "dub":
        # Dub stage: overlay TTS audio onto video
        from backend.core.tts import TTSService
        # Get latest video asset
        result = await db.execute(
            select(VideoAsset)
            .where(VideoAsset.project_id == project_id)
            .order_by(VideoAsset.created_at.desc())
        )
        last_asset = result.scalars().first()
        input_video = last_asset.filepath if last_asset else project.source_filepath or ""

        if not input_video or not os.path.exists(input_video):
            raise HTTPException(400, "No input video available for dub stage")

        # Generate TTS audio
        tts_service = TTSService()
        script = stage.params.get("script", "这是一个AI生成的视频介绍") if stage.params else "这是一个AI生成的视频介绍"
        audio_path = str(Path(input_video).parent / (Path(input_video).stem + "_dub.mp3"))
        await tts_service.synthesize(text=script, output_path=audio_path)

        # Merge audio onto video
        output_video = str(Path(input_video).with_name(
            Path(input_video).stem + "_dub" + Path(input_video).suffix
        ))
        cmd = [
            "ffmpeg", "-y", "-i", input_video, "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v:0", "-map", "1:a:0", "-map", "0:a:0?",
            output_video,
        ]
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            stage.status = StageStatus.COMPLETED
            stage.output_filepath = output_video
            stage.output_url = output_video
            asset = VideoAsset(
                project_id=project_id,
                filename=Path(output_video).name,
                filepath=output_video,
                asset_type="output",
                source_stage="dub",
            )
            db.add(asset)
            project.source_filepath = output_video
        else:
            stage.status = StageStatus.FAILED
            stage.error_log = result.stderr[:500]

    elif stage_name == "face_swap":
        from backend.core.face_swap import face_swap_video
        # Input: source file or latest asset
        result = await db.execute(
            select(VideoAsset)
            .where(VideoAsset.project_id == project_id)
            .order_by(VideoAsset.created_at.desc())
        )
        last_asset = result.scalars().first()
        input_video = last_asset.filepath if last_asset else project.source_filepath or ""

        if not input_video or not os.path.exists(input_video):
            raise HTTPException(400, "No input video available for face swap")

        output_video = str(Path(input_video).with_name(
            Path(input_video).stem + "_faceswapped" + Path(input_video).suffix
        ))

        # Get reference face config from stage params
        config = stage.params or {}
        if isinstance(config, str):
            config = json.loads(config)
        ref_image = config.get("ref_image", "")

        if not ref_image or not os.path.exists(ref_image):
            raise HTTPException(400, "ref_image required in stage.params. Set ref_image path before running face_swap.")

        logging.getLogger(__name__).info(
            "Starting face_swap: input=%s ref=%s", input_video, ref_image
        )

        res = face_swap_video(
            input_video=input_video,
            output_video=output_video,
            ref_image_path=ref_image,
        )

        if res.get("success"):
            stage.status = StageStatus.COMPLETED
            stage.output_filepath = output_video
            stage.output_url = output_video
            stage.duration_seconds = float(res.get("total_frames", 0) / 30)
            asset = VideoAsset(
                project_id=project_id,
                filename=Path(output_video).name,
                filepath=output_video,
                asset_type="output",
                source_stage="face_swap",
            )
            db.add(asset)
            project.source_filepath = output_video
        else:
            stage.status = StageStatus.FAILED
            stage.error_log = res.get("error", "Unknown face swap error")

    elif stage_name == "lip_sync":
        # Lip sync stage: requires GPU + LatentSync
        raise HTTPException(400, "Lip sync requires GPU + LatentSync. Please install first.")

    else:
        # Placeholder for other stages
        raise HTTPException(400, f"Stage '{stage_name}' is not implemented yet")

    stage.completed_at = datetime.utcnow()
    stage.duration_seconds = (stage.completed_at - stage.started_at).total_seconds() if stage.started_at else 0
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