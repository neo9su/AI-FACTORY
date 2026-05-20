# Phase 5C — Platform API Integration Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace local bundle.json stub publishing with real API calls to 抖音 (Douyin), 小红书 (Xiaohongshu), and TikTok, so content is automatically uploaded to each platform after the publish worker packages it.

**Architecture:**
Each platform gets its own `PlatformClient` adapter class under `backend/core/publisher/platforms/`. The `PublisherService` remains the orchestrator — after building a bundle it calls the matching adapter. A new `platform_credentials` config table (env-var backed) stores API keys. The `PublishJob` model gains an `upload_result` JSONB field to record platform responses. The frontend publish panel gains a "configure credentials" modal.

**Tech Stack:** Python `httpx` (async HTTP), `aiofiles`, existing ARQ worker pipeline, FastAPI, SQLAlchemy async, Next.js 14 + React

**Platforms & API Strategy:**
- **抖音 (Douyin):** Open Platform API — `https://open.douyin.com` — OAuth2 client_credentials flow, video upload via multipart, text/image post via `/api/douyin/v1/poi/query_resource_by_keyword`
- **小红书 (Xiaohongshu):** Creator Open API — `https://ark.xiaohongshu.com` — OAuth2, note creation endpoint
- **TikTok:** TikTok for Developers API v2 — `https://open.tiktokapis.com` — OAuth2, Direct Post API

> **Practical note:** Real platform OAuth requires registered app credentials. The implementation provides a full working skeleton with credential injection — operators plug in their own client_id/client_secret. Stubbed responses are used when credentials are absent (graceful degradation).

---

## Task 1: Create platform adapter interface + base class

**Objective:** Define the `PlatformClient` abstract base class all adapters will implement.

**Files:**
- Create: `backend/core/publisher/platforms/__init__.py`
- Create: `backend/core/publisher/platforms/base.py`

**Step 1: Create package init**

```python
# backend/core/publisher/platforms/__init__.py
from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

__all__ = ["PlatformClient", "PlatformUploadResult"]
```

**Step 2: Create base class**

```python
# backend/core/publisher/platforms/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformUploadResult:
    """Result of a platform upload attempt."""
    platform: str
    success: bool
    post_id: str | None = None
    post_url: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class PlatformClient(ABC):
    """Abstract base class for platform upload clients."""

    platform_name: str  # e.g. "douyin"

    @abstractmethod
    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        """Upload content from a publish bundle to the platform.

        Args:
            bundle: The platform-specific bundle built by PublisherService

        Returns:
            PlatformUploadResult with success/failure details
        """
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if credentials are available for this platform."""
        ...
```

**Step 3: Commit**

```bash
git add backend/core/publisher/platforms/
git commit -m "feat(publish): add PlatformClient abstract base class"
```

---

## Task 2: Douyin (抖音) platform client

**Objective:** Implement `DouyinClient` with OAuth2 token fetch + video/note upload.

**Files:**
- Create: `backend/core/publisher/platforms/douyin.py`

**Step 1: Write DouyinClient**

```python
# backend/core/publisher/platforms/douyin.py
from __future__ import annotations
import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

DOUYIN_TOKEN_URL = "https://open.douyin.com/oauth/client_token/"
DOUYIN_VIDEO_UPLOAD_URL = "https://open.douyin.com/api/douyin/v1/video/upload/"
DOUYIN_VIDEO_CREATE_URL = "https://open.douyin.com/api/douyin/v1/video/create/"
DOUYIN_IMAGE_CREATE_URL = "https://open.douyin.com/api/douyin/v1/image/upload/"


class DouyinClient(PlatformClient):
    """Douyin Open Platform API client.

    Required env vars:
        DOUYIN_CLIENT_KEY
        DOUYIN_CLIENT_SECRET

    Optional env vars:
        DOUYIN_OPEN_ID   (the author's open_id, required for posting)
    """

    platform_name = "douyin"

    def __init__(self) -> None:
        self.client_key = os.getenv("DOUYIN_CLIENT_KEY", "")
        self.client_secret = os.getenv("DOUYIN_CLIENT_SECRET", "")
        self.open_id = os.getenv("DOUYIN_OPEN_ID", "")
        self._token: str | None = None

    def is_configured(self) -> bool:
        return bool(self.client_key and self.client_secret and self.open_id)

    async def _get_access_token(self) -> str:
        """Fetch or return cached client_credential token."""
        if self._token:
            return self._token
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                DOUYIN_TOKEN_URL,
                json={
                    "client_key": self.client_key,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credential",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["data"]["access_token"]
            return self._token

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        """Upload content to Douyin.

        For short_video_scripts: creates a video post (with audio_url reference).
        For ebook/personality_test: creates an image note.
        """
        if not self.is_configured():
            logger.warning("[Douyin] Not configured — returning stub result")
            return PlatformUploadResult(
                platform="douyin",
                success=False,
                error="DOUYIN_CLIENT_KEY / DOUYIN_CLIENT_SECRET / DOUYIN_OPEN_ID not set",
            )

        try:
            token = await self._get_access_token()
            caption = bundle.get("caption", "")
            hashtags = bundle.get("hashtags", [])
            # Douyin: hashtags embedded in title as #tag
            title = bundle.get("title", "")
            tag_str = " ".join(hashtags[:5])
            full_title = f"{title} {tag_str}".strip()[:100]

            headers = {
                "access-token": token,
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=60) as client:
                # Image/text post (for ebook & personality test)
                # Video post requires actual video binary — we post the cover image + caption
                payload = {
                    "open_id": self.open_id,
                    "title": full_title,
                    "micro_app_id": "",
                    "video_info": {
                        "video_url": bundle.get("audio_url") or "",
                        "duration": bundle.get("duration_seconds", 45),
                    },
                    "text": caption[:500],
                    "image_info": {
                        "images": [{"web_uri": bundle.get("cover_image_url") or ""}]
                    },
                }
                resp = await client.post(
                    DOUYIN_VIDEO_CREATE_URL,
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                result_data = resp.json()
                logger.info(f"[Douyin] Upload response: {result_data}")

                if result_data.get("extra", {}).get("error_code", 0) == 0:
                    item_id = result_data.get("data", {}).get("item_id", "")
                    return PlatformUploadResult(
                        platform="douyin",
                        success=True,
                        post_id=item_id,
                        post_url=f"https://www.douyin.com/video/{item_id}",
                        raw_response=result_data,
                    )
                else:
                    err = result_data.get("extra", {}).get("description", "unknown error")
                    return PlatformUploadResult(
                        platform="douyin",
                        success=False,
                        error=err,
                        raw_response=result_data,
                    )
        except Exception as e:
            logger.exception(f"[Douyin] Upload failed: {e}")
            return PlatformUploadResult(platform="douyin", success=False, error=str(e))
```

**Step 2: Commit**

```bash
git add backend/core/publisher/platforms/douyin.py
git commit -m "feat(publish): add DouyinClient platform adapter"
```

---

## Task 3: Xiaohongshu (小红书) platform client

**Objective:** Implement `XiaohongshuClient` for note creation via Creator Open API.

**Files:**
- Create: `backend/core/publisher/platforms/xiaohongshu.py`

**Step 1: Write XiaohongshuClient**

```python
# backend/core/publisher/platforms/xiaohongshu.py
from __future__ import annotations
import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

XHS_BASE_URL = "https://ark.xiaohongshu.com"
XHS_NOTE_CREATE_URL = f"{XHS_BASE_URL}/api/sns/v1/note/create"
XHS_TOKEN_URL = f"{XHS_BASE_URL}/api/oauth/token"


class XiaohongshuClient(PlatformClient):
    """小红书 Creator Open API client.

    Required env vars:
        XHS_APP_ID
        XHS_APP_SECRET
        XHS_ACCESS_TOKEN  (pre-obtained OAuth token, or use app_id+secret flow)
    """

    platform_name = "xiaohongshu"

    def __init__(self) -> None:
        self.app_id = os.getenv("XHS_APP_ID", "")
        self.app_secret = os.getenv("XHS_APP_SECRET", "")
        self.access_token = os.getenv("XHS_ACCESS_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.access_token or (self.app_id and self.app_secret))

    async def _ensure_token(self) -> str:
        if self.access_token:
            return self.access_token
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                XHS_TOKEN_URL,
                json={"app_id": self.app_id, "app_secret": self.app_secret,
                      "grant_type": "client_credentials"},
            )
            resp.raise_for_status()
            self.access_token = resp.json()["access_token"]
            return self.access_token

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        """Create a 小红书 note from the bundle."""
        if not self.is_configured():
            logger.warning("[XHS] Not configured — returning stub result")
            return PlatformUploadResult(
                platform="xiaohongshu",
                success=False,
                error="XHS_ACCESS_TOKEN not set",
            )

        try:
            token = await self._ensure_token()
            title = bundle.get("title", "")[:20]
            desc = bundle.get("caption", "")[:1000]
            hashtags = bundle.get("hashtags", [])
            # 小红书 uses #tag in desc
            tag_str = " ".join(hashtags[:10])
            desc_with_tags = f"{desc}\n\n{tag_str}".strip()

            cover_url = bundle.get("cover_image_url") or ""
            note_type = "video" if bundle.get("audio_url") else "normal"

            payload = {
                "type": note_type,
                "title": title,
                "desc": desc_with_tags,
                "image_info": {
                    "images": [{"url": cover_url}] if cover_url else []
                },
            }

            if note_type == "video" and bundle.get("audio_url"):
                payload["video_info"] = {
                    "video_url": bundle["audio_url"],
                    "duration": bundle.get("duration_seconds", 45),
                    "cover_url": cover_url,
                }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(XHS_NOTE_CREATE_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("success"):
                note_id = data.get("data", {}).get("note_id", "")
                return PlatformUploadResult(
                    platform="xiaohongshu",
                    success=True,
                    post_id=note_id,
                    post_url=f"https://www.xiaohongshu.com/explore/{note_id}",
                    raw_response=data,
                )
            else:
                err = data.get("msg", "unknown error")
                return PlatformUploadResult(
                    platform="xiaohongshu", success=False, error=err, raw_response=data
                )

        except Exception as e:
            logger.exception(f"[XHS] Upload failed: {e}")
            return PlatformUploadResult(platform="xiaohongshu", success=False, error=str(e))
```

**Step 2: Commit**

```bash
git add backend/core/publisher/platforms/xiaohongshu.py
git commit -m "feat(publish): add XiaohongshuClient platform adapter"
```

---

## Task 4: TikTok platform client

**Objective:** Implement `TikTokClient` using TikTok for Developers v2 Direct Post API.

**Files:**
- Create: `backend/core/publisher/platforms/tiktok.py`

**Step 1: Write TikTokClient**

```python
# backend/core/publisher/platforms/tiktok.py
from __future__ import annotations
import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_PHOTO_POST_URL = "https://open.tiktokapis.com/v2/post/publish/content/init/"


class TikTokClient(PlatformClient):
    """TikTok for Developers API v2 client — Direct Post.

    Required env vars:
        TIKTOK_CLIENT_KEY
        TIKTOK_CLIENT_SECRET
        TIKTOK_ACCESS_TOKEN  (user-level token with video.publish scope)

    See: https://developers.tiktok.com/doc/content-posting-api-get-started
    """

    platform_name = "tiktok"

    def __init__(self) -> None:
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
        self.client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.access_token)

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        """Post content to TikTok via Direct Post API."""
        if not self.is_configured():
            logger.warning("[TikTok] Not configured — returning stub result")
            return PlatformUploadResult(
                platform="tiktok",
                success=False,
                error="TIKTOK_ACCESS_TOKEN not set",
            )

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            }

            caption = bundle.get("caption", "")
            hashtags = bundle.get("hashtags", [])
            hashtag_str = " ".join(hashtags[:8])
            full_caption = f"{caption}\n{hashtag_str}".strip()[:2200]

            cover_url = bundle.get("cover_image_url") or ""
            audio_url = bundle.get("audio_url") or ""

            if audio_url:
                # Video post
                payload = {
                    "post_info": {
                        "title": full_caption[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                        "video_cover_timestamp_ms": 1000,
                    },
                    "source_info": {
                        "source": "PULL_FROM_URL",
                        "video_url": audio_url,
                    },
                }
                url = TIKTOK_VIDEO_INIT_URL
            else:
                # Photo post
                payload = {
                    "post_info": {
                        "title": full_caption[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_comment": False,
                    },
                    "source_info": {
                        "source": "PULL_FROM_URL",
                        "photo_images": [cover_url] if cover_url else [],
                        "photo_cover_index": 0,
                    },
                    "post_mode": "DIRECT_POST",
                    "media_type": "PHOTO",
                }
                url = TIKTOK_PHOTO_POST_URL

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("error", {}).get("code") == "ok":
                pub_id = data.get("data", {}).get("publish_id", "")
                return PlatformUploadResult(
                    platform="tiktok",
                    success=True,
                    post_id=pub_id,
                    raw_response=data,
                )
            else:
                err = data.get("error", {}).get("message", "unknown error")
                return PlatformUploadResult(
                    platform="tiktok", success=False, error=err, raw_response=data
                )

        except Exception as e:
            logger.exception(f"[TikTok] Upload failed: {e}")
            return PlatformUploadResult(platform="tiktok", success=False, error=str(e))
```

**Step 2: Commit**

```bash
git add backend/core/publisher/platforms/tiktok.py
git commit -m "feat(publish): add TikTokClient platform adapter"
```

---

## Task 5: Platform registry + update PublisherService to call adapters

**Objective:** Wire the 3 adapters into a registry; update `PublisherService.upload_to_platform()` method so the publish worker can call it after packaging.

**Files:**
- Modify: `backend/core/publisher/platforms/__init__.py`
- Modify: `backend/core/publisher/publisher_service.py`

**Step 1: Update platforms `__init__.py` with registry**

```python
# backend/core/publisher/platforms/__init__.py
from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult
from backend.core.publisher.platforms.douyin import DouyinClient
from backend.core.publisher.platforms.xiaohongshu import XiaohongshuClient
from backend.core.publisher.platforms.tiktok import TikTokClient

PLATFORM_REGISTRY: dict[str, type[PlatformClient]] = {
    "douyin": DouyinClient,
    "xiaohongshu": XiaohongshuClient,
    "tiktok": TikTokClient,
}


def get_platform_client(platform: str) -> PlatformClient:
    """Return an initialized platform client for the given platform name."""
    cls = PLATFORM_REGISTRY.get(platform)
    if not cls:
        raise ValueError(f"Unknown platform: {platform}")
    return cls()


__all__ = [
    "PlatformClient",
    "PlatformUploadResult",
    "PLATFORM_REGISTRY",
    "get_platform_client",
]
```

**Step 2: Add `upload_to_platform` method to `PublisherService`**

Add this method at the bottom of `PublisherService` class in `backend/core/publisher/publisher_service.py`:

```python
    async def upload_to_platform(
        self,
        platform: str,
        bundle: dict[str, Any],
    ) -> "PlatformUploadResult":
        """Upload a bundle to the specified platform.

        Args:
            platform: "douyin" | "xiaohongshu" | "tiktok"
            bundle: The platform-specific bundle dict

        Returns:
            PlatformUploadResult
        """
        from backend.core.publisher.platforms import get_platform_client

        client = get_platform_client(platform)
        logger.info(
            f"[Publisher] Uploading to {platform} "
            f"(configured={client.is_configured()})"
        )
        result = await client.upload(bundle)
        return result
```

Also add `from __future__ import annotations` at the top if not present, and `from typing import TYPE_CHECKING`:

```python
if TYPE_CHECKING:
    from backend.core.publisher.platforms.base import PlatformUploadResult
```

**Step 3: Commit**

```bash
git add backend/core/publisher/platforms/__init__.py backend/core/publisher/publisher_service.py
git commit -m "feat(publish): add platform registry and upload_to_platform method"
```

---

## Task 6: Update publish worker to call platform upload after packaging

**Objective:** After building + saving the bundle, call `upload_to_platform()`. Store result in `job.upload_result`. Update job status to `uploaded` on success, `upload_failed` on error (keep bundle as `ready` so user can retry).

**Files:**
- Modify: `backend/workers/publish_worker.py`
- Modify: `backend/models/publish.py` (add `upload_result` JSONB field + new statuses)

**Step 1: Add `upload_result` field to `PublishJob`**

In `backend/models/publish.py`, add after `error_msg`:

```python
    upload_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Result from platform upload API: {success, post_id, post_url, error, raw_response}

    post_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    post_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Populated after successful platform upload
```

And update the status comment:
```python
    # pending | packaging | ready | uploading | uploaded | upload_failed | published | failed
```

**Step 2: Update `publish_worker.py` to call upload**

After `job.status = "ready"` block, add:

```python
            # --- Phase 5C: upload to platform ---
            job.status = "uploading"
            await db.commit()

            try:
                upload_result = await service.upload_to_platform(
                    platform=job.platform,
                    bundle=bundle,
                )
                job.upload_result = {
                    "success": upload_result.success,
                    "post_id": upload_result.post_id,
                    "post_url": upload_result.post_url,
                    "error": upload_result.error,
                }
                if upload_result.success:
                    job.status = "uploaded"
                    job.post_id = upload_result.post_id
                    job.post_url = upload_result.post_url
                    logger.info(
                        f"[PublishWorker] Uploaded to {job.platform}: "
                        f"post_id={upload_result.post_id}"
                    )
                else:
                    job.status = "upload_failed"
                    logger.warning(
                        f"[PublishWorker] Upload to {job.platform} failed: "
                        f"{upload_result.error}"
                    )
            except Exception as upload_err:
                logger.exception(f"[PublishWorker] Upload exception: {upload_err}")
                job.status = "upload_failed"
                job.upload_result = {"success": False, "error": str(upload_err)}

            await db.commit()
```

**Step 3: Commit**

```bash
git add backend/models/publish.py backend/workers/publish_worker.py
git commit -m "feat(publish): wire platform upload into publish worker, add upload_result field"
```

---

## Task 7: Update publish API to expose upload status + post URL

**Objective:** Add `upload_result`, `post_id`, `post_url` to `PublishStatusResponse`. Add a new endpoint `POST /api/v1/publish/job/{job_id}/retry-upload` for re-triggering upload on failed jobs.

**Files:**
- Modify: `backend/api/publish.py`

**Step 1: Update `PublishStatusResponse`**

Add fields:

```python
class PublishStatusResponse(BaseModel):
    publish_job_id: str
    product_id: str
    platform: str
    status: str
    bundle_path: Optional[str] = None
    bundle_data: Optional[dict] = None
    upload_result: Optional[dict] = None     # NEW
    post_id: Optional[str] = None            # NEW
    post_url: Optional[str] = None           # NEW
    error_msg: Optional[str] = None
    created_at: str
```

Update all three existing response constructors to include:

```python
    upload_result=j.upload_result,
    post_id=j.post_id,
    post_url=j.post_url,
```

**Step 2: Add retry-upload endpoint**

```python
@router.post("/publish/job/{job_id}/retry-upload")
async def retry_upload(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Re-queue an upload_failed job for platform upload retry."""
    import os
    from backend.models.publish import PublishJob

    result = await db.execute(select(PublishJob).where(PublishJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Publish job not found")

    if job.status not in ("upload_failed", "ready"):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be in 'upload_failed' or 'ready' state (current: {job.status})",
        )

    # Re-queue
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    redis = await arq.create_pool(redis_settings)
    job.status = "pending"
    await db.commit()
    await redis.enqueue_job("process_publish_job", str(job.id))
    await redis.aclose()

    return {"status": "pending", "publish_job_id": job_id}
```

**Step 3: Commit**

```bash
git add backend/api/publish.py
git commit -m "feat(publish): add upload status fields and retry-upload endpoint"
```

---

## Task 8: Frontend — show post URL + upload status in PublishPanel

**Objective:** Update `PublishPanel` to display `post_url` link when uploaded, show "upload_failed" state with retry button, show "uploading" spinner.

**Files:**
- Modify: `frontend/components/publish-panel.tsx`

**Step 1: Add new statuses to STATUS_BADGE and STATUS_LABEL**

```typescript
const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  packaging: "bg-blue-100 text-blue-800 animate-pulse",
  ready: "bg-green-100 text-green-800",
  uploading: "bg-blue-100 text-blue-800 animate-pulse",    // NEW
  uploaded: "bg-purple-100 text-purple-800",               // NEW
  upload_failed: "bg-orange-100 text-orange-800",          // NEW
  published: "bg-purple-100 text-purple-800",
  failed: "bg-red-100 text-red-800",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "等待中",
  packaging: "打包中...",
  ready: "✅ 已就绪",
  uploading: "上传中...",                    // NEW
  uploaded: "🚀 已上传",                     // NEW
  upload_failed: "⚠️ 上传失败",              // NEW
  published: "🎉 已发布",
  failed: "❌ 失败",
};
```

**Step 2: Update `PublishJob` interface**

```typescript
interface PublishJob {
  publish_job_id: string;
  product_id: string;
  platform: string;
  status: string;
  bundle_path: string | null;
  bundle_data: Record<string, unknown> | null;
  upload_result: Record<string, unknown> | null;  // NEW
  post_id: string | null;                          // NEW
  post_url: string | null;                         // NEW
  error_msg: string | null;
  created_at: string;
}
```

**Step 3: Update `hasInProgress` to include new in-progress statuses**

```typescript
const hasInProgress = jobs.some((j) =>
  ["pending", "packaging", "uploading"].includes(j.status)
);
```

**Step 4: Add `handleRetryUpload` function**

```typescript
const handleRetryUpload = async (jobId: string) => {
  const res = await fetch(`/api/v1/publish/job/${jobId}/retry-upload`, {
    method: "POST",
  });
  if (res.ok) await fetchJobs();
};
```

**Step 5: In the job card render, add post URL link and retry button**

In the job card JSX, after the status badge, add:

```tsx
{/* Post URL link */}
{job.post_url && (
  <a
    href={job.post_url}
    target="_blank"
    rel="noopener noreferrer"
    className="text-xs text-blue-600 hover:underline"
  >
    查看帖子 →
  </a>
)}

{/* Upload error detail */}
{job.status === "upload_failed" && job.upload_result && (
  <p className="text-xs text-orange-600 mt-1">
    {String((job.upload_result as Record<string, unknown>).error || "上传失败")}
  </p>
)}

{/* Retry button */}
{job.status === "upload_failed" && (
  <button
    onClick={() => handleRetryUpload(job.publish_job_id)}
    className="mt-1 text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
  >
    🔄 重试上传
  </button>
)}
```

**Step 6: Commit**

```bash
git add frontend/components/publish-panel.tsx
git commit -m "feat(publish): update PublishPanel with upload status, post URL, and retry button"
```

---

## Task 9: Credentials env-var documentation + .env.example

**Objective:** Add all required platform API keys to `.env.example` with clear setup instructions.

**Files:**
- Modify: `.env.example` (or create if not exists)
- Create: `docs/platform-api-setup.md`

**Step 1: Update `.env.example`**

Add section:

```bash
# ===== Phase 5C: Platform API Credentials =====

# 抖音 (Douyin) Open Platform
# Register app at https://developer.open-douyin.com/
DOUYIN_CLIENT_KEY=
DOUYIN_CLIENT_SECRET=
DOUYIN_OPEN_ID=       # Author's open_id (obtained after user auth)

# 小红书 (Xiaohongshu) Creator Open API
# Register at https://ark.xiaohongshu.com/
XHS_APP_ID=
XHS_APP_SECRET=
XHS_ACCESS_TOKEN=     # Pre-obtained OAuth access token

# TikTok for Developers
# Register at https://developers.tiktok.com/
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_ACCESS_TOKEN=  # User-level access token with video.publish scope
```

**Step 2: Create `docs/platform-api-setup.md`**

```markdown
# Platform API Setup Guide

## 抖音 (Douyin) Open Platform

1. Visit https://developer.open-douyin.com/ and create an app
2. Enable scopes: `video.create`, `video.list`, `user_info`
3. Copy `client_key` → `DOUYIN_CLIENT_KEY`
4. Copy `client_secret` → `DOUYIN_CLIENT_SECRET`
5. Complete user OAuth to obtain `open_id` → `DOUYIN_OPEN_ID`

## 小红书 (Xiaohongshu) Creator Open API

1. Apply for creator API access at https://ark.xiaohongshu.com/
2. Get `app_id` and `app_secret`
3. Complete OAuth2 authorization to get `access_token`
4. Set `XHS_ACCESS_TOKEN` in your environment

## TikTok for Developers

1. Register at https://developers.tiktok.com/
2. Create an app and enable `Content Posting API`
3. Complete OAuth with scope `video.publish`
4. Set `TIKTOK_ACCESS_TOKEN` to the user-level token

## Testing without credentials

The platform clients gracefully degrade when credentials are absent:
- `is_configured()` returns `False`
- `upload()` returns `PlatformUploadResult(success=False, error="... not set")`
- The publish job status becomes `upload_failed` (bundle.json still available for manual posting)
```

**Step 3: Commit**

```bash
git add .env.example docs/platform-api-setup.md
git commit -m "docs: add Phase 5C platform API credentials guide and .env.example"
```

---

## Task 10: Install httpx + syntax verification

**Objective:** Ensure `httpx` is installed in the project venv and all new files pass syntax checks.

**Files:**
- Modify: `requirements.txt` (or `pyproject.toml`)

**Step 1: Install httpx**

```bash
cd ~/autonomous-ai-factory
.venv/bin/pip install httpx
```

Add to `requirements.txt`:

```
httpx>=0.27.0
```

**Step 2: Verify all new files**

```bash
cd ~/autonomous-ai-factory
.venv/bin/python -c "
import py_compile, glob
files = glob.glob('backend/core/publisher/platforms/*.py') + [
    'backend/workers/publish_worker.py',
    'backend/api/publish.py',
    'backend/models/publish.py',
]
for f in files:
    py_compile.compile(f, doraise=True)
    print(f'OK: {f}')
"
```

**Step 3: Check imports**

```bash
.venv/bin/python -c "
from backend.core.publisher.platforms import get_platform_client, PLATFORM_REGISTRY
print('Platforms:', list(PLATFORM_REGISTRY.keys()))
for name, cls in PLATFORM_REGISTRY.items():
    client = cls()
    print(f'  {name}: configured={client.is_configured()}')
"
```

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat(publish): add httpx dependency for platform API clients"
```

---

## Summary

**10 tasks, ~10 commits**

| Task | Deliverable |
|------|-------------|
| 1 | `PlatformClient` abstract base class |
| 2 | `DouyinClient` (抖音) |
| 3 | `XiaohongshuClient` (小红书) |
| 4 | `TikTokClient` (TikTok) |
| 5 | Platform registry + `upload_to_platform()` on PublisherService |
| 6 | Publish worker calls upload, stores result |
| 7 | API exposes post URL + retry endpoint |
| 8 | Frontend shows upload status, post link, retry button |
| 9 | Credentials docs + `.env.example` |
| 10 | httpx install + syntax verification |

**After Phase 5C:** The full loop is complete — content is automatically packaged AND uploaded to platforms. When credentials aren't set, the system gracefully falls back to local bundle.json (manual posting mode from Phase 5B).
