from __future__ import annotations
import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

TIKTOK_VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_PHOTO_POST_URL = "https://open.tiktokapis.com/v2/post/publish/content/init/"


class TikTokClient(PlatformClient):
    """TikTok for Developers API v2 client - Direct Post.
    Required env vars: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN
    """
    platform_name = "tiktok"

    def __init__(self) -> None:
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
        self.client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.access_token)

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        if not self.is_configured():
            logger.warning("[TikTok] Not configured")
            return PlatformUploadResult(platform="tiktok", success=False, error="TIKTOK_ACCESS_TOKEN not set")
        try:
            headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json; charset=UTF-8"}
            caption = bundle.get("caption", "")
            hashtags = bundle.get("hashtags", [])
            hashtag_str = " ".join(hashtags[:8])
            full_caption = f"{caption}\n{hashtag_str}".strip()[:2200]
            cover_url = bundle.get("cover_image_url") or ""
            audio_url = bundle.get("audio_url") or ""
            if audio_url:
                payload = {
                    "post_info": {"title": full_caption[:150], "privacy_level": "PUBLIC_TO_EVERYONE", "disable_duet": False, "disable_comment": False, "disable_stitch": False, "video_cover_timestamp_ms": 1000},
                    "source_info": {"source": "PULL_FROM_URL", "video_url": audio_url},
                }
                url = TIKTOK_VIDEO_INIT_URL
            else:
                payload = {
                    "post_info": {"title": full_caption[:150], "privacy_level": "PUBLIC_TO_EVERYONE", "disable_comment": False},
                    "source_info": {"source": "PULL_FROM_URL", "photo_images": [cover_url] if cover_url else [], "photo_cover_index": 0},
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
                return PlatformUploadResult(platform="tiktok", success=True, post_id=pub_id, raw_response=data)
            else:
                err = data.get("error", {}).get("message", "unknown error")
                return PlatformUploadResult(platform="tiktok", success=False, error=err, raw_response=data)
        except Exception as e:
            logger.exception(f"[TikTok] Upload failed: {e}")
            return PlatformUploadResult(platform="tiktok", success=False, error=str(e))
