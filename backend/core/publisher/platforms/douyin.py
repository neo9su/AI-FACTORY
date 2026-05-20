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

    async def _get_session_cookies(self) -> list[dict] | None:
        """Fetch most recent logged_in Douyin session cookies from DB."""
        try:
            from backend.db.session import AsyncSessionLocal
            from backend.models.platform_session import PlatformSession
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(PlatformSession)
                    .where(
                        PlatformSession.platform == self.platform_name,
                        PlatformSession.status == "logged_in",
                    )
                    .order_by(PlatformSession.created_at.desc())
                    .limit(1)
                )
                session = result.scalar_one_or_none()
                if session and session.cookies:
                    return session.cookies
        except Exception as e:
            logger.warning(f"[Douyin] Failed to get session cookies: {e}")
        return None

    async def _upload_with_cookies(
        self, bundle: dict, cookies: list[dict]
    ) -> PlatformUploadResult:
        """Post to Douyin using saved browser cookies (fallback to bundle storage on API change)."""
        import httpx
        cookie_header = "; ".join(
            f"{c['name']}={c['value']}" for c in cookies[:30]
        )
        headers = {
            "Cookie": cookie_header,
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.douyin.com/",
            "Content-Type": "application/json",
        }
        api_url = "https://open.douyin.com/api/douyin/v1/video/create/"
        payload = {
            "title": bundle.get("title", "")[:20],
            "desc": bundle.get("caption", ""),
            "type": "video",
            "tag_list": [
                {"id": "", "name": tag.lstrip("#")}
                for tag in bundle.get("hashtags", [])[:5]
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(api_url, json=payload, headers=headers)
                data = resp.json() if resp.text else {}
                if resp.status_code == 200 and data.get("success"):
                    item_id = data.get("data", {}).get("item_id", "")
                    return PlatformUploadResult(
                        platform=self.platform_name,
                        success=True,
                        post_id=item_id,
                        post_url=f"https://www.douyin.com/video/{item_id}",
                        raw_response=data,
                    )
                else:
                    return PlatformUploadResult(
                        platform=self.platform_name,
                        success=False,
                        error=f"[Douyin] cookie upload error {resp.status_code}: {data}",
                        raw_response=data,
                    )
        except Exception as e:
            return PlatformUploadResult(
                platform=self.platform_name, success=False, error=str(e)
            )

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        """Upload to Douyin: try cookie-based auth first, then API key."""
        cookies = await self._get_session_cookies()
        if cookies:
            return await self._upload_with_cookies(bundle, cookies)
        if not self.is_configured():
            logger.warning("[Douyin] Not configured")
            return PlatformUploadResult(
                platform=self.platform_name,
                success=False,
                error="credentials not configured (no active session and no API key)",
            )
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
