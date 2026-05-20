"""Trends API — 热点信号管理"""
from __future__ import annotations

from typing import Optional

import arq
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.trend import TrendScanJob, TrendSignal
from backend.workers.pipeline import WorkerSettings

router = APIRouter()


class TrendScanRequest(BaseModel):
    sources: list[str] = ["reddit"]
    limit: int = 20


class TrendSignalResponse(BaseModel):
    id: str
    source: str
    title: str
    url: Optional[str]
    engagement_score: float
    viral_score: float
    analyzed: bool
    emotion_tags: Optional[list]
    pain_points: Optional[list]

    model_config = ConfigDict(from_attributes=True)


@router.post("/trends/scan")
async def trigger_trend_scan(
    request: TrendScanRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """触发热点扫描（ARQ 异步入队）"""
    # 创建 job 记录
    job_record = TrendScanJob(status="queued", sources=request.sources)
    session.add(job_record)
    await session.commit()
    await session.refresh(job_record)

    # 入队 ARQ
    redis = await arq.create_pool(WorkerSettings.redis_settings)
    await redis.enqueue_job("run_trend_scan", request.sources)
    await redis.aclose()

    return {
        "status": "queued",
        "job_id": job_record.id,
        "message": f"Scan queued for: {request.sources}",
    }


@router.get("/trends/scan/{job_id}")
async def get_scan_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """查询扫描任务状态"""
    result = await session.execute(select(TrendScanJob).where(TrendScanJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "sources": job.sources,
        "scanned_count": job.scanned_count,
        "opportunities_count": job.opportunities_count,
        "error_msg": job.error_msg,
        "created_at": job.created_at.isoformat(),
    }


@router.get("/trends", response_model=list[TrendSignalResponse])
async def list_trends(
    limit: int = 20,
    source: Optional[str] = None,
    analyzed_only: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """获取最新热点信号"""
    query = select(TrendSignal).order_by(desc(TrendSignal.engagement_score)).limit(limit)
    if source:
        query = query.where(TrendSignal.source == source)
    if analyzed_only:
        query = query.where(TrendSignal.analyzed == True)  # noqa: E712
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/trends/{trend_id}", response_model=TrendSignalResponse)
async def get_trend(
    trend_id: str,
    session: AsyncSession = Depends(get_db),
):
    """获取单个热点信号详情"""
    result = await session.execute(select(TrendSignal).where(TrendSignal.id == trend_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Trend signal not found")
    return signal


@router.post("/trends/{trend_id}/analyze")
async def analyze_trend(
    trend_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """触发单个热点的情绪分析"""
    # TODO: Phase 1 Brain 实现后接入
    return {"status": "queued", "trend_id": trend_id, "message": "Analysis queued"}
