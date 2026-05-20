# Phase 5-B: Auto-Publish Pipeline Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a simulated auto-publish system that packages NeuroTrend generated products (video scripts + TTS audio + SD cover images) into publish-ready bundles, tracks publish history, exposes publish APIs, and displays publish status in the dashboard — with real clipboard/file export as the actual "publish" action (since 抖音/小红书/TikTok require manual login/OAuth which is not available in this environment).

**Architecture:**
- `PublishJob` DB model tracks publish attempts per product per platform
- `PublisherService` packages content into a platform-specific bundle (title + caption + hashtags + audio URL + cover image URL)
- `publish_worker.py` ARQ worker executes async publish jobs
- REST API at `/api/v1/publish` to trigger and query publish jobs
- Dashboard panel "📤 Publish Queue" shows queue status and export bundles
- Export: JSON bundle saved to `static/publish/<product_id>/<platform>/bundle.json` — user downloads it and manually posts

**Tech Stack:** FastAPI, SQLAlchemy async, ARQ, PostgreSQL, Next.js 14, TypeScript

---

## Task 1: Create PublishJob DB Model

**Objective:** Add `publish_jobs` table to track publish attempts per product per platform

**Files:**
- Create: `backend/models/publish.py`
- Modify: `backend/models/__init__.py`
- Modify: `backend/db/init_db.py` (import new model so create_all picks it up)

**Step 1: Write the model**

```python
# backend/models/publish.py
"""Phase 5-B — Publish job tracking model."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text
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
```

**Step 2: Add back-reference to ContentProduct in trend.py**

In `backend/models/trend.py`, inside the `ContentProduct` class, add after the `engagements` relationship:

```python
    publish_jobs: Mapped[list["PublishJob"]] = relationship(  # noqa: F821
        "PublishJob", back_populates="product", cascade="all, delete-orphan"
    )
```

Also add to TYPE_CHECKING imports at top of `trend.py`:
```python
if TYPE_CHECKING:
    from backend.models.publish import PublishJob  # noqa: F401
```

**Step 3: Register model so create_all picks it up**

In `backend/models/__init__.py`, add:
```python
from backend.models.publish import PublishJob  # noqa: F401
```

In `backend/db/init_db.py`, add the import:
```python
from backend.models import publish  # noqa: F401
```

**Step 4: Verify import compiles**

```bash
cd ~/autonomous-ai-factory
.venv/bin/python -c "from backend.models.publish import PublishJob; print('OK')"
```
Expected: `OK`

**Step 5: Commit**
```bash
git add backend/models/publish.py backend/models/trend.py backend/models/__init__.py backend/db/init_db.py
git commit -m "feat(publish): add PublishJob DB model"
```

---

## Task 2: Create PublisherService (Platform Bundle Builder)

**Objective:** Build the core service that packages a `ContentProduct` into a platform-optimized publish bundle

**Files:**
- Create: `backend/core/publisher/__init__.py`
- Create: `backend/core/publisher/publisher_service.py`

**Step 1: Write publisher_service.py**

```python
# backend/core/publisher/publisher_service.py
"""Platform-specific publish bundle builder.

Packages a ContentProduct into a platform-optimized bundle:
- Selects best script based on viral_potential score
- Formats caption with hashtags per platform style
- References TTS audio URL and SD cover image URL
- Saves bundle.json to static/publish/<product_id>/<platform>/
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PLATFORM_HASHTAG_LIMITS = {
    "douyin": 5,       # 抖音 recommend 3-5 tags
    "xiaohongshu": 10, # 小红书 supports many tags
    "tiktok": 8,       # TikTok 5-8 tags
}

PLATFORM_CAPTION_LIMITS = {
    "douyin": 500,
    "xiaohongshu": 1000,
    "tiktok": 300,
}


class PublisherService:
    """Packages ContentProduct data into platform-specific publish bundles."""

    def __init__(self, static_dir: Path | None = None) -> None:
        self.static_dir = static_dir or (Path.home() / "autonomous-ai-factory/static")

    def build_bundle(
        self,
        product_id: str,
        product_type: str,
        product_meta: dict[str, Any],
        platform: str,
        tts_audio_urls: list[dict] | None = None,
        cover_image_url: str | None = None,
    ) -> dict[str, Any]:
        """Build a publish bundle for a specific platform.

        Args:
            product_id: ContentProduct UUID
            product_type: ebook | personality_test | short_video_scripts
            product_meta: ContentProduct.meta dict (AI-generated content)
            platform: douyin | xiaohongshu | tiktok
            tts_audio_urls: list of {script_id, url, duration_hint}
            cover_image_url: URL to SD-generated cover image

        Returns:
            Platform-optimized publish bundle dict
        """
        if product_type == "short_video_scripts":
            return self._bundle_video_scripts(
                product_id, product_meta, platform, tts_audio_urls, cover_image_url
            )
        elif product_type == "ebook":
            return self._bundle_ebook(
                product_id, product_meta, platform, cover_image_url
            )
        elif product_type == "personality_test":
            return self._bundle_personality_test(
                product_id, product_meta, platform, cover_image_url
            )
        else:
            raise ValueError(f"Unknown product_type: {product_type}")

    def _bundle_video_scripts(
        self,
        product_id: str,
        meta: dict[str, Any],
        platform: str,
        tts_audio_urls: list[dict] | None,
        cover_image_url: str | None,
    ) -> dict[str, Any]:
        """Bundle video scripts — picks best script by viral_potential."""
        scripts = meta.get("scripts", [])
        if not scripts:
            raise ValueError("No scripts found in product meta")

        # Pick script with highest viral_potential
        best_script = max(scripts, key=lambda s: s.get("viral_potential", 0))
        script_id = best_script.get("id", 1)

        # Find matching TTS audio
        audio_url = None
        if tts_audio_urls:
            for item in tts_audio_urls:
                if str(item.get("script_id")) == str(script_id):
                    audio_url = item.get("url")
                    break
            if not audio_url and tts_audio_urls:
                audio_url = tts_audio_urls[0].get("url")

        # Platform-specific hashtags
        hashtags = best_script.get("hashtags", [])
        limit = PLATFORM_HASHTAG_LIMITS.get(platform, 5)
        hashtags = hashtags[:limit]

        # Build caption
        caption = best_script.get("caption", "")
        cap_limit = PLATFORM_CAPTION_LIMITS.get(platform, 500)
        if len(caption) > cap_limit:
            caption = caption[:cap_limit - 3] + "..."

        # Full narration text (for manual posting reference)
        narration_parts = [
            seg.get("narration", "") for seg in best_script.get("script", [])
        ]
        narration_text = "\n".join(filter(None, narration_parts))

        return {
            "platform": platform,
            "product_id": product_id,
            "product_type": "short_video_scripts",
            "selected_script_id": script_id,
            "title": best_script.get("title", ""),
            "hook_line": best_script.get("hook_line", ""),
            "caption": caption,
            "hashtags": hashtags,
            "duration_seconds": best_script.get("duration_seconds", 45),
            "format": best_script.get("format", "口播"),
            "bgm_style": best_script.get("bgm_style", "轻音乐"),
            "narration_text": narration_text,
            "audio_url": audio_url,
            "cover_image_url": cover_image_url,
            "posting_strategy": meta.get("posting_strategy", {}),
            "viral_potential": best_script.get("viral_potential", 0),
            "series_concept": meta.get("series_concept", ""),
        }

    def _bundle_ebook(
        self,
        product_id: str,
        meta: dict[str, Any],
        platform: str,
        cover_image_url: str | None,
    ) -> dict[str, Any]:
        """Bundle ebook for social media promotion post."""
        marketing_angles = meta.get("marketing_angles", [])
        limit = PLATFORM_HASHTAG_LIMITS.get(platform, 5)

        # Build hashtags from title words
        title = meta.get("title", "")
        hashtags = [f"#{w}" for w in title.split()[:3] if w]
        hashtags += ["#电子书", "#自我成长", "#心理学"]
        hashtags = hashtags[:limit]

        caption = f"{meta.get('sales_page_headline', title)}\n\n{meta.get('tagline', '')}"
        if marketing_angles:
            caption += "\n\n" + "\n".join(f"✅ {a}" for a in marketing_angles[:3])
        caption += f"\n\n👇 评论区留言「{meta.get('price_suggestion', '$9.9')}」获取"

        return {
            "platform": platform,
            "product_id": product_id,
            "product_type": "ebook",
            "title": meta.get("title", ""),
            "subtitle": meta.get("subtitle", ""),
            "tagline": meta.get("tagline", ""),
            "caption": caption[:PLATFORM_CAPTION_LIMITS.get(platform, 500)],
            "hashtags": hashtags,
            "cover_image_url": cover_image_url,
            "price_suggestion": meta.get("price_suggestion", "$9.9"),
            "intro_sample": meta.get("intro_sample", "")[:200],
            "audio_url": None,
        }

    def _bundle_personality_test(
        self,
        product_id: str,
        meta: dict[str, Any],
        platform: str,
        cover_image_url: str | None,
    ) -> dict[str, Any]:
        """Bundle personality test as interactive content teaser."""
        limit = PLATFORM_HASHTAG_LIMITS.get(platform, 5)
        test_name = meta.get("test_name", "心理测试")
        hashtags = [f"#{test_name}", "#MBTI", "#心理测试", "#性格测试", "#自我探索"][:limit]

        caption = f"🧠 {test_name}\n\n{meta.get('description', '')}"
        caption += "\n\n👇 点击主页链接免费测试"

        return {
            "platform": platform,
            "product_id": product_id,
            "product_type": "personality_test",
            "title": test_name,
            "caption": caption[:PLATFORM_CAPTION_LIMITS.get(platform, 500)],
            "hashtags": hashtags,
            "cover_image_url": cover_image_url,
            "audio_url": None,
        }

    def save_bundle(
        self, product_id: str, platform: str, bundle: dict[str, Any]
    ) -> str:
        """Save bundle JSON to static dir and return relative URL path."""
        output_dir = self.static_dir / "publish" / product_id / platform
        output_dir.mkdir(parents=True, exist_ok=True)

        bundle_path = output_dir / "bundle.json"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))

        relative_url = f"/static/publish/{product_id}/{platform}/bundle.json"
        logger.info(f"[Publisher] Bundle saved to {bundle_path}")
        return relative_url
```

**Step 2: Create __init__.py**
```python
# backend/core/publisher/__init__.py
```

**Step 3: Verify import**
```bash
cd ~/autonomous-ai-factory
.venv/bin/python -c "from backend.core.publisher.publisher_service import PublisherService; print('OK')"
```
Expected: `OK`

**Step 4: Commit**
```bash
git add backend/core/publisher/
git commit -m "feat(publish): add PublisherService platform bundle builder"
```

---

## Task 3: Create publish_worker.py ARQ Worker

**Objective:** Async ARQ worker that runs publish packaging jobs in the background

**Files:**
- Create: `backend/workers/publish_worker.py`
- Modify: `backend/workers/pipeline.py` (register worker in WorkerSettings)

**Step 1: Write publish_worker.py**

```python
# backend/workers/publish_worker.py
"""ARQ worker for async publish job processing."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from backend.core.publisher.publisher_service import PublisherService
from backend.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ["douyin", "xiaohongshu", "tiktok"]


async def process_publish_job(
    ctx: dict[str, Any],
    publish_job_id: str,
) -> dict[str, Any]:
    """ARQ worker: package a ContentProduct into a publish bundle.

    Args:
        ctx: ARQ worker context
        publish_job_id: PublishJob.id

    Returns:
        dict with status and bundle_path
    """
    from backend.models.publish import PublishJob
    from backend.models.trend import ContentProduct

    logger.info(f"[PublishWorker] Processing publish job {publish_job_id}")

    async with AsyncSessionLocal() as db:
        # Load publish job
        result = await db.execute(
            select(PublishJob).where(PublishJob.id == publish_job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            return {"status": "failed", "error": "job not found"}

        # Load product
        result2 = await db.execute(
            select(ContentProduct).where(ContentProduct.id == job.product_id)
        )
        product = result2.scalar_one_or_none()
        if not product:
            job.status = "failed"
            job.error_msg = "product not found"
            await db.commit()
            return {"status": "failed", "error": "product not found"}

        # Update status to packaging
        job.status = "packaging"
        await db.commit()

        try:
            service = PublisherService()
            bundle = service.build_bundle(
                product_id=str(product.id),
                product_type=product.product_type,
                product_meta=product.meta or {},
                platform=job.platform,
                tts_audio_urls=product.tts_audio_urls,
                cover_image_url=_get_cover_url(product),
            )
            bundle_path = service.save_bundle(
                product_id=str(product.id),
                platform=job.platform,
                bundle=bundle,
            )

            job.status = "ready"
            job.bundle_path = bundle_path
            job.bundle_data = bundle
            await db.commit()

            logger.info(f"[PublishWorker] Job {publish_job_id} ready: {bundle_path}")
            return {
                "status": "ready",
                "publish_job_id": publish_job_id,
                "bundle_path": bundle_path,
            }

        except Exception as e:
            logger.exception(f"[PublishWorker] Job {publish_job_id} failed: {e}")
            job.status = "failed"
            job.error_msg = str(e)
            await db.commit()
            return {"status": "failed", "error": str(e)}


def _get_cover_url(product: Any) -> str | None:
    """Extract cover image URL from product meta."""
    meta = product.meta or {}
    # Check common locations
    return (
        meta.get("cover_image_url")
        or meta.get("cover_url")
        or (product.content_url if product.content_url and ".png" in (product.content_url or "") else None)
    )
```

**Step 2: Register in pipeline.py WorkerSettings**

In `backend/workers/pipeline.py`, find the `WorkerSettings` class and add `process_publish_job` to the functions list:

```python
from backend.workers.publish_worker import process_publish_job

class WorkerSettings:
    functions = [
        run_project_pipeline,
        run_single_stage,
        run_trend_scan,
        analyze_single_trend,
        generate_content_product,
        recalculate_scores,
        generate_tts_audio,
        process_publish_job,  # Phase 5-B
    ]
```

**Step 3: Verify import**
```bash
cd ~/autonomous-ai-factory
.venv/bin/python -c "from backend.workers.publish_worker import process_publish_job; print('OK')"
```
Expected: `OK`

**Step 4: Commit**
```bash
git add backend/workers/publish_worker.py backend/workers/pipeline.py
git commit -m "feat(publish): add publish_worker ARQ job"
```

---

## Task 4: Publish REST API

**Objective:** REST endpoints to trigger publish jobs and query their status

**Files:**
- Create: `backend/api/publish.py`
- Modify: `backend/main.py` (register router)

**Step 1: Write publish API**

```python
# backend/api/publish.py
"""Phase 5-B — Publish job REST API."""
from __future__ import annotations

import logging
from typing import Any

import arq
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_PLATFORMS = ["douyin", "xiaohongshu", "tiktok"]


class PublishRequest(BaseModel):
    product_id: str
    platforms: list[str]  # ["douyin", "xiaohongshu", "tiktok"]


class PublishStatusResponse(BaseModel):
    publish_job_id: str
    product_id: str
    platform: str
    status: str
    bundle_path: str | None = None
    bundle_data: dict | None = None
    error_msg: str | None = None
    created_at: str


@router.post("/publish/trigger")
async def trigger_publish(
    request: PublishRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger publish packaging jobs for a product across requested platforms.

    Creates a PublishJob for each platform and queues ARQ workers.
    Returns list of created job IDs.
    """
    from backend.models.publish import PublishJob
    from backend.models.trend import ContentProduct

    # Validate product exists
    result = await db.execute(
        select(ContentProduct).where(ContentProduct.id == request.product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate product is ready
    if product.status not in ("ready", "done", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"Product not ready for publishing (status={product.status})"
        )

    # Validate platforms
    invalid = [p for p in request.platforms if p not in SUPPORTED_PLATFORMS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platforms: {invalid}. Supported: {SUPPORTED_PLATFORMS}"
        )

    # Create PublishJob for each platform
    created_jobs = []
    redis = await arq.create_pool(RedisSettings())

    for platform in request.platforms:
        # Check if already pending/ready for this platform
        existing = await db.execute(
            select(PublishJob).where(
                PublishJob.product_id == request.product_id,
                PublishJob.platform == platform,
                PublishJob.status.in_(["pending", "packaging", "ready"]),
            )
        )
        if existing.scalar_one_or_none():
            logger.info(f"[PublishAPI] Skipping {platform} — already has active job")
            continue

        job = PublishJob(
            product_id=request.product_id,
            platform=platform,
            status="pending",
        )
        db.add(job)
        await db.flush()  # get the ID

        # Queue ARQ worker
        await redis.enqueue_job(
            "process_publish_job",
            str(job.id),
        )
        created_jobs.append({"publish_job_id": str(job.id), "platform": platform})

    await db.commit()
    await redis.aclose()

    return {
        "product_id": request.product_id,
        "jobs_created": len(created_jobs),
        "jobs": created_jobs,
    }


@router.get("/publish/jobs/{product_id}")
async def get_publish_jobs(
    product_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PublishStatusResponse]:
    """Get all publish jobs for a product."""
    from backend.models.publish import PublishJob

    result = await db.execute(
        select(PublishJob)
        .where(PublishJob.product_id == product_id)
        .order_by(PublishJob.created_at.desc())
    )
    jobs = result.scalars().all()

    return [
        PublishStatusResponse(
            publish_job_id=str(j.id),
            product_id=str(j.product_id),
            platform=j.platform,
            status=j.status,
            bundle_path=j.bundle_path,
            bundle_data=j.bundle_data,
            error_msg=j.error_msg,
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]


@router.get("/publish/job/{job_id}")
async def get_publish_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> PublishStatusResponse:
    """Get a specific publish job by ID."""
    from backend.models.publish import PublishJob

    result = await db.execute(
        select(PublishJob).where(PublishJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Publish job not found")

    return PublishStatusResponse(
        publish_job_id=str(job.id),
        product_id=str(job.product_id),
        platform=job.platform,
        status=job.status,
        bundle_path=job.bundle_path,
        bundle_data=job.bundle_data,
        error_msg=job.error_msg,
        created_at=job.created_at.isoformat(),
    )


@router.post("/publish/job/{job_id}/mark-published")
async def mark_as_published(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Mark a ready publish job as published (user manually posted the content)."""
    from backend.models.publish import PublishJob

    result = await db.execute(
        select(PublishJob).where(PublishJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Publish job not found")

    if job.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'ready' state (current: {job.status})"
        )

    job.status = "published"
    await db.commit()
    return {"status": "published", "publish_job_id": job_id}
```

**Step 2: Register router in main.py**

In `backend/main.py`, add:
```python
from backend.api import analytics, notify, opportunities, projects, publish, tasks, trends, ws
# ... existing includes ...
app.include_router(publish.router, prefix="/api/v1", tags=["publish"])
```

**Step 3: Verify import**
```bash
cd ~/autonomous-ai-factory
.venv/bin/python -c "from backend.api.publish import router; print('OK')"
```
Expected: `OK`

**Step 4: Commit**
```bash
git add backend/api/publish.py backend/main.py
git commit -m "feat(publish): add publish REST API endpoints"
```

---

## Task 5: Frontend — Publish Panel Component

**Objective:** Add a "📤 Publish" panel to the product detail page that shows publish status and bundle download

**Files:**
- Create: `frontend/components/publish-panel.tsx`
- Modify: Relevant product detail page to include the panel

**Step 1: Write publish-panel.tsx**

```tsx
// frontend/components/publish-panel.tsx
"use client";

import { useState, useEffect } from "react";

interface PublishJob {
  publish_job_id: string;
  product_id: string;
  platform: string;
  status: string; // pending | packaging | ready | published | failed
  bundle_path: string | null;
  bundle_data: Record<string, unknown> | null;
  error_msg: string | null;
  created_at: string;
}

interface PublishPanelProps {
  productId: string;
  productStatus: string;
}

const PLATFORM_LABELS: Record<string, string> = {
  douyin: "🎵 抖音",
  xiaohongshu: "📕 小红书",
  tiktok: "🌐 TikTok",
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  packaging: "bg-blue-100 text-blue-800 animate-pulse",
  ready: "bg-green-100 text-green-800",
  published: "bg-purple-100 text-purple-800",
  failed: "bg-red-100 text-red-800",
};

export default function PublishPanel({ productId, productStatus }: PublishPanelProps) {
  const [jobs, setJobs] = useState<PublishJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(["douyin", "xiaohongshu"]);

  const canPublish = ["ready", "done", "completed"].includes(productStatus);

  const fetchJobs = async () => {
    const res = await fetch(`/api/v1/publish/jobs/${productId}`);
    if (res.ok) {
      const data = await res.json();
      setJobs(data);
    }
  };

  useEffect(() => {
    fetchJobs();
    // Poll every 5s if any job is in progress
    const interval = setInterval(() => {
      if (jobs.some((j) => ["pending", "packaging"].includes(j.status))) {
        fetchJobs();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [productId, jobs.length]);

  const handleTrigger = async () => {
    if (!selectedPlatforms.length) return;
    setTriggering(true);
    try {
      const res = await fetch("/api/v1/publish/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, platforms: selectedPlatforms }),
      });
      if (res.ok) await fetchJobs();
    } finally {
      setTriggering(false);
    }
  };

  const handleMarkPublished = async (jobId: string) => {
    const res = await fetch(`/api/v1/publish/job/${jobId}/mark-published`, {
      method: "POST",
    });
    if (res.ok) await fetchJobs();
  };

  const downloadBundle = (job: PublishJob) => {
    if (!job.bundle_data) return;
    const blob = new Blob([JSON.stringify(job.bundle_data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${job.platform}-bundle.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">📤 发布到平台</h3>
        {!canPublish && (
          <span className="text-sm text-gray-400">等待内容生成完成...</span>
        )}
      </div>

      {canPublish && (
        <div className="space-y-3">
          {/* Platform selector */}
          <div className="flex gap-2 flex-wrap">
            {Object.entries(PLATFORM_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() =>
                  setSelectedPlatforms((prev) =>
                    prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
                  )
                }
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                  selectedPlatforms.includes(key)
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-gray-600 border-gray-300 hover:border-indigo-400"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <button
            onClick={handleTrigger}
            disabled={triggering || !selectedPlatforms.length}
            className="w-full py-2 px-4 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            {triggering ? "⏳ 正在打包..." : "🚀 生成发布包"}
          </button>
        </div>
      )}

      {/* Publish jobs list */}
      {jobs.length > 0 && (
        <div className="space-y-2">
          {jobs.map((job) => (
            <div
              key={job.publish_job_id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">
                  {PLATFORM_LABELS[job.platform] || job.platform}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[job.status] || "bg-gray-100 text-gray-600"}`}
                >
                  {job.status === "pending" && "等待中"}
                  {job.status === "packaging" && "打包中..."}
                  {job.status === "ready" && "✅ 已就绪"}
                  {job.status === "published" && "🎉 已发布"}
                  {job.status === "failed" && "❌ 失败"}
                </span>
              </div>

              <div className="flex gap-2">
                {job.status === "ready" && (
                  <>
                    <button
                      onClick={() => downloadBundle(job)}
                      className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                    >
                      ⬇️ 下载包
                    </button>
                    <button
                      onClick={() => handleMarkPublished(job.publish_job_id)}
                      className="text-xs px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700"
                    >
                      ✔ 标记已发
                    </button>
                  </>
                )}
                {job.status === "failed" && job.error_msg && (
                  <span className="text-xs text-red-500 max-w-[200px] truncate" title={job.error_msg}>
                    {job.error_msg}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {jobs.length === 0 && canPublish && (
        <p className="text-sm text-gray-400 text-center py-4">
          选择平台并点击「生成发布包」开始打包
        </p>
      )}
    </div>
  );
}
```

**Step 2: Find and update the product detail page**

Search for where `ContentProduct` or `tts-player` is rendered:
```bash
grep -r "tts-player\|product_type\|ContentProduct" ~/autonomous-ai-factory/frontend --include="*.tsx" -l
```

In the product detail page/component, import and add `PublishPanel`:
```tsx
import PublishPanel from "@/components/publish-panel";
// ...
<PublishPanel productId={product.id} productStatus={product.status} />
```

**Step 3: Commit**
```bash
git add frontend/components/publish-panel.tsx
git commit -m "feat(publish): add PublishPanel frontend component"
```

---

## Task 6: Wire SD Cover Image into Product Meta

**Objective:** Ensure `SDImageService.generate_cover()` is called from `factory_worker.py` and the cover URL is stored in `product.meta`

**Files:**
- Modify: `backend/workers/factory_worker.py`

**Step 1: Read current factory_worker.py**
```bash
cat ~/autonomous-ai-factory/backend/workers/factory_worker.py
```

**Step 2: Add SD cover generation after content generation**

After the content is generated and before saving to DB, add:
```python
from backend.core.image.sd_service import SDImageService

# Generate SD cover image
cover_url = None
try:
    sd = SDImageService()
    topic = opportunity_data.get("topic", "")
    emotions = opportunity_data.get("core_emotions", [])
    emotion_str = "、".join(emotions[:3]) if emotions else "情绪疗愈"
    prompt = f"Chinese woman, emotional healing, {topic}, {emotion_str}, soft lighting, portrait, 35mm film"
    cover_path = await sd.generate_cover(
        prompt=prompt,
        product_id=product_id,
    )
    if cover_path:
        cover_url = f"/static/images/{cover_path.split('/')[-1]}" if "/" in cover_path else cover_path
except Exception as e:
    logger.warning(f"[FactoryWorker] SD cover generation failed: {e}")

# Store cover URL in content dict
if cover_url and isinstance(content, dict):
    content["cover_image_url"] = cover_url
```

**Step 3: Verify factory_worker.py compiles**
```bash
cd ~/autonomous-ai-factory
.venv/bin/python -c "from backend.workers.factory_worker import generate_content_product; print('OK')"
```
Expected: `OK`

**Step 4: Commit**
```bash
git add backend/workers/factory_worker.py
git commit -m "feat(publish): wire SD cover generation into factory worker"
```

---

## Task 7: Final Integration Check & Git Commit

**Objective:** Verify all components integrate cleanly

**Step 1: Full import check**
```bash
cd ~/autonomous-ai-factory
.venv/bin/python -c "
from backend.models.publish import PublishJob
from backend.core.publisher.publisher_service import PublisherService
from backend.workers.publish_worker import process_publish_job
from backend.api.publish import router
print('All imports OK')
"
```
Expected: `All imports OK`

**Step 2: Syntax check all new files**
```bash
cd ~/autonomous-ai-factory
.venv/bin/python -m py_compile \
  backend/models/publish.py \
  backend/core/publisher/publisher_service.py \
  backend/workers/publish_worker.py \
  backend/api/publish.py \
  && echo "Syntax OK"
```
Expected: `Syntax OK`

**Step 3: Final commit**
```bash
git add -A
git commit -m "feat: Phase 5-B auto-publish complete — bundle builder + ARQ worker + REST API + dashboard panel"
```

**Step 4: Verify commit count**
```bash
git log --oneline | head -5
git log --oneline | wc -l
```
Expected: 35+ commits

---

## Summary

Phase 5-B delivers:

| Component | Purpose |
|-----------|---------|
| `PublishJob` model | Track publish attempts per product per platform |
| `PublisherService` | Package product into platform-optimized JSON bundle |
| `publish_worker.py` | ARQ async worker to run packaging jobs |
| `publish` API | REST endpoints to trigger + query + mark-published |
| `PublishPanel` component | Frontend UI — select platforms, download bundles, mark published |
| SD cover wired | Cover images included in all publish bundles |

**Publish flow:**
1. User opens product → clicks "🚀 生成发布包"
2. Frontend POSTs to `/api/v1/publish/trigger`
3. ARQ worker runs `process_publish_job` → builds bundle.json
4. Bundle saved to `static/publish/<id>/<platform>/bundle.json`
5. User clicks "⬇️ 下载包" → gets JSON with title/caption/hashtags/audio_url/cover_url/narration
6. User manually posts on 抖音/小红书/TikTok using the bundle content
7. User clicks "✔ 标记已发" → job marked `published`
