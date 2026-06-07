"""Bilibili Open Platform API client.

Uploads videos to Bilibili (B站) using Open Platform API.
Env vars: BILIBILI_APP_ID, BILIBILI_APP_SECRET, BILIBILI_ACCESS_TOKEN
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

BILI_TOKEN_URL = "https://api.bilibili.com/x/vas/oauth2/token"
BILI_VIDEO_UPLOAD_URL = "https://member.bilibili.com/x/vup/archive/video"


class BilibiliClient(PlatformClient):
    """Bilibili Open Platform client.

    Required env vars:
        BILIBILI_APP_ID
        BILIBILI_APP_SECRET
        BILIBILI_ACCESS_TOKEN
    """
    platform_name = "bilibili"

    def __init__(self) -> None:
        self.app_id = os.getenv("BILIBILI_APP_ID", "")
        self.app_secret = os.getenv("BILIBILI_APP_SECRET", "")
        self.access_token = os.getenv("BILIBILI_ACCESS_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret and self.access_token)

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        if not self.is_configured():
            logger.warning("[Bilibili] Not configured")
            return PlatformUploadResult(
                platform="bilibili",
                success=False,
                error="BILIBILI_APP_ID / BILIBILI_ACCESS_TOKEN not set",
            )

        title = bundle.get("title", "AI视频")[:80]
        caption = bundle.get("caption", "")
        hashtags = bundle.get("hashtags", [])
        tag_str = " ".join(hashtags[:6])

        payload = {
            "access_token": self.access_token,
            "app_id": self.app_id,
            "title": title,
            "content": f"{caption}\n{tag_str}".strip()[:2000],
            "video_url": bundle.get("audio_url") or bundle.get("video_url", ""),
            "cover_url": bundle.get("cover_image_url", ""),
            "source": "ai_factory",
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(BILI_VIDEO_UPLOAD_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code") == 0:
                video_id = data.get("data", {}).get("bvid", "")
                return PlatformUploadResult(
                    platform="bilibili",
                    success=True,
                    post_id=video_id,
                    post_url=f"https://www.bilibili.com/video/{video_id}",
                    raw_response=data,
                )
            else:
                err = data.get("message", "unknown error")
                return PlatformUploadResult(
                    platform="bilibili",
                    success=False,
                    error=f"Bilibili API error: {err}",
                    raw_response=data,
                )
        except Exception as e:
            logger.exception(f"[Bilibili] Upload failed: {e}")
            return PlatformUploadResult(
                platform="bilibili", success=False, error=str(e)
            )
