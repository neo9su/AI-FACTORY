"""
FastAPI application entry point for Autonomous AI Software Factory.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import analytics, auth, deploy as deploy_api, health as health_api, notify, opportunities, platform_login, projects, publish, settings, stats, tasks, trends, video_projects, workspace, ws
from backend.api import optimizer as optimizer_api  # Phase 5-C
from backend.db.session import engine
from backend.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager - handles startup and shutdown."""
    # Startup: create all database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown: cleanup
    await engine.dispose()


app = FastAPI(
    title="Autonomous AI Software Factory",
    description="AI-powered autonomous software development platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files for TTS audio and other generated assets
STATIC_DIR = Path.home() / "autonomous-ai-factory/static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8648", "http://frontend:3000", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(notify.router, prefix="/api/v1", tags=["notifications"])
app.include_router(ws.router, tags=["websocket"])
app.include_router(trends.router, prefix="/api/v1", tags=["trends"])
app.include_router(opportunities.router, prefix="/api/v1", tags=["opportunities"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(publish.router, prefix="/api/v1", tags=["publish"])
app.include_router(workspace.router, prefix="/api/v1", tags=["workspace"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
app.include_router(health_api.router, prefix="/api/v1", tags=["health"])
app.include_router(settings.router, prefix="/api/v1", tags=["settings"])
app.include_router(platform_login.router, prefix="/api", tags=["platform-login"])
app.include_router(optimizer_api.router, prefix="/api/v1", tags=["optimizer"])  # Phase 5-C
app.include_router(deploy_api.router, prefix="/api/v1", tags=["deploy"])

# Auth routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Video production pipeline
app.include_router(video_projects.router, prefix="/api/v1", tags=["video-pipeline"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
