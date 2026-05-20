from __future__ import annotations
import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

DOUYIN_TOKEN_URL = "https://open.douyin.com/oauth/client_token/"
DOUYIN_VIDEO_CREATE_URL = "https://open.douyin.com/api/douyin/v1/video/create/"


class DouyinClient(PlatformClient):
    """Douyin Open Platform API client.
    Required env vars: DOUYIN_CLIENT_KEY, DOUYIN_CLIENT_SECRET, DOUYIN_OPEN_ID
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
        if self._token:
            return self._token
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                DOUYIN_TOKEN_URL,
                json={"client_key": self.client_key, "client_secret": self.client_secret, "grant_type": "client_credential"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["data"]["access_token"]
            return self._token

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        if not self.is_configured():
            logger.warning("[Douyin] Not configured")
            return PlatformUploadResult(platform="douyin", success=False, error="DOUYIN_CLIENT_KEY / DOUYIN_CLIENT_SECRET / DOUYIN_OPEN_ID not set")
        try:
            token = await self._get_access_token()
            hashtags = bundle.get("hashtags", [])
            title = bundle.get("title", "")
            tag_str = " ".join(hashtags[:5])
            full_title = f"{title} {tag_str}".strip()[:100]
            headers = {"access-token": token, "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {
                    "open_id": self.open_id,
                    "title": full_title,
                    "micro_app_id": "",
                    "video_info": {"video_url": bundle.get("audio_url") or "", "duration": bundle.get("duration_seconds", 45)},
                    "text": bundle.get("caption", "")[:500],
                    "image_info": {"images": [{"web_uri": bundle.get("cover_image_url") or ""}]},
                }
                resp = await client.post(DOUYIN_VIDEO_CREATE_URL, headers=headers, json=payload)
                resp.raise_for_status()
                result_data = resp.json()
            if result_data.get("extra", {}).get("error_code", 0) == 0:
                item_id = result_data.get("data", {}).get("item_id", "")
                return PlatformUploadResult(platform="douyin", success=True, post_id=item_id, post_url=f"https://www.douyin.com/video/{item_id}", raw_response=result_data)
            else:
                err = result_data.get("extra", {}).get("description", "unknown error")
                return PlatformUploadResult(platform="douyin", success=False, error=err, raw_response=result_data)
        except Exception as e:
            logger.exception(f"[Douyin] Upload failed: {e}")
            return PlatformUploadResult(platform="douyin", success=False, error=str(e))
