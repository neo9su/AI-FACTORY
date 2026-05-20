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
    Required env vars: XHS_APP_ID, XHS_APP_SECRET, XHS_ACCESS_TOKEN
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
            resp = await client.post(XHS_TOKEN_URL, json={"app_id": self.app_id, "app_secret": self.app_secret, "grant_type": "client_credentials"})
            resp.raise_for_status()
            self.access_token = resp.json()["access_token"]
            return self.access_token

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        if not self.is_configured():
            logger.warning("[XHS] Not configured")
            return PlatformUploadResult(platform="xiaohongshu", success=False, error="XHS_ACCESS_TOKEN not set")
        try:
            token = await self._ensure_token()
            title = bundle.get("title", "")[:20]
            desc = bundle.get("caption", "")[:1000]
            hashtags = bundle.get("hashtags", [])
            tag_str = " ".join(hashtags[:10])
            desc_with_tags = f"{desc}\n\n{tag_str}".strip()
            cover_url = bundle.get("cover_image_url") or ""
            note_type = "video" if bundle.get("audio_url") else "normal"
            payload = {
                "type": note_type,
                "title": title,
                "desc": desc_with_tags,
                "image_info": {"images": [{"url": cover_url}] if cover_url else []},
            }
            if note_type == "video" and bundle.get("audio_url"):
                payload["video_info"] = {"video_url": bundle["audio_url"], "duration": bundle.get("duration_seconds", 45), "cover_url": cover_url}
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(XHS_NOTE_CREATE_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            if data.get("success"):
                note_id = data.get("data", {}).get("note_id", "")
                return PlatformUploadResult(platform="xiaohongshu", success=True, post_id=note_id, post_url=f"https://www.xiaohongshu.com/explore/{note_id}", raw_response=data)
            else:
                return PlatformUploadResult(platform="xiaohongshu", success=False, error=data.get("msg", "unknown error"), raw_response=data)
        except Exception as e:
            logger.exception(f"[XHS] Upload failed: {e}")
            return PlatformUploadResult(platform="xiaohongshu", success=False, error=str(e))
