"""Trends API — 热点信号管理"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.trend import TrendSignal

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
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """触发热点扫描任务（异步后台）"""
    # TODO: Phase 1 实现后接入 ARQ worker
    return {
        "status": "queued",
        "message": f"Trend scan queued for sources: {request.sources}",
        "sources": request.sources,
    }


@router.get("/trends", response_model=list[TrendSignalResponse])
async def list_trends(
    limit: int = 20,
    source: Optional[str] = None,
    analyzed_only: bool = False,
    session: AsyncSession = Depends(get_db),
) -> list[TrendSignal]:
    """获取最新热点信号"""
    query = select(TrendSignal).order_by(desc(TrendSignal.engagement_score)).limit(limit)
    if source:
        query = query.where(TrendSignal.source == source)
    if analyzed_only:
        query = query.where(TrendSignal.analyzed == True)  # noqa: E712
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/trends/{trend_id}")
async def get_trend(
    trend_id: str,
    session: AsyncSession = Depends(get_db),
) -> TrendSignal:
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
