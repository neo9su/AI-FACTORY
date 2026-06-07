"""Kuaishou (快手) Open Platform API client.

Uploads videos to Kuaishou using Open Platform API.
Env vars: KUAISHOU_APP_ID, KUAISHOU_APP_SECRET, KUAISHOU_ACCESS_TOKEN
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

KUAISHOU_TOKEN_URL = "https://open.kuaishou.com/oauth2/access_token"
KUAISHOU_VIDEO_UPLOAD_URL = "https://open.kuaishou.com/openapi/v1/photo/upload"


class KuaishouClient(PlatformClient):
    """Kuaishou Open Platform client.

    Required env vars:
        KUAISHOU_APP_ID
        KUAISHOU_APP_SECRET
        KUAISHOU_ACCESS_TOKEN
    """
    platform_name = "kuaishou"

    def __init__(self) -> None:
        self.app_id = os.getenv("KUAISHOU_APP_ID", "")
        self.app_secret = os.getenv("KUAISHOU_APP_SECRET", "")
        self.access_token = os.getenv("KUAISHOU_ACCESS_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret and self.access_token)

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        if not self.is_configured():
            logger.warning("[Kuaishou] Not configured")
            return PlatformUploadResult(
                platform="kuaishou",
                success=False,
                error="KUAISHOU_APP_ID / KUAISHOU_ACCESS_TOKEN not set",
            )

        title = bundle.get("title", "AI视频")[:60]
        caption = bundle.get("caption", "")
        hashtags = bundle.get("hashtags", [])
        tag_str = " ".join(hashtags[:5])

        payload = {
            "access_token": self.access_token,
            "app_id": self.app_id,
            "title": title,
            "caption": f"{caption}\n{tag_str}".strip()[:1000],
            "video_url": bundle.get("audio_url") or bundle.get("video_url", ""),
            "cover_url": bundle.get("cover_image_url", ""),
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(KUAISHOU_VIDEO_UPLOAD_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("result") == 1:
                photo_id = data.get("photo_id", "")
                return PlatformUploadResult(
                    platform="kuaishou",
                    success=True,
                    post_id=photo_id,
                    post_url=f"https://www.kuaishou.com/photo/{photo_id}",
                    raw_response=data,
                )
            else:
                err = data.get("error_msg", "unknown error")
                return PlatformUploadResult(
                    platform="kuaishou",
                    success=False,
                    error=f"Kuaishou API error: {err}",
                    raw_response=data,
                )
        except Exception as e:
            logger.exception(f"[Kuaishou] Upload failed: {e}")
            return PlatformUploadResult(
                platform="kuaishou", success=False, error=str(e)
            )
