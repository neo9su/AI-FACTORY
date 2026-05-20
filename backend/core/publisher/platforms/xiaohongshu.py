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

    async def _get_session_cookies(self) -> list[dict] | None:
        """Fetch most recent logged_in XHS session cookies from DB."""
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
            logger.warning(f"[XHS] Failed to get session cookies: {e}")
        return None

    async def _upload_with_cookies(
        self, bundle: dict, cookies: list[dict]
    ) -> PlatformUploadResult:
        """Post to XHS using saved browser cookies (fallback to bundle storage on API change)."""
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
            "Referer": "https://www.xiaohongshu.com/",
            "Content-Type": "application/json",
        }
        api_url = "https://www.xiaohongshu.com/api/sns/v3/note"
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
                    note_id = data.get("data", {}).get("note_id", "")
                    return PlatformUploadResult(
                        platform=self.platform_name,
                        success=True,
                        post_id=note_id,
                        post_url=f"https://www.xiaohongshu.com/explore/{note_id}",
                        raw_response=data,
                    )
                else:
                    return PlatformUploadResult(
                        platform=self.platform_name,
                        success=False,
                        error=f"XHS cookie upload error {resp.status_code}: {data}",
                        raw_response=data,
                    )
        except Exception as e:
            return PlatformUploadResult(
                platform=self.platform_name, success=False, error=str(e)
            )

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        """Upload to XHS: try cookie-based auth first, then API key."""
        cookies = await self._get_session_cookies()
        if cookies:
            return await self._upload_with_cookies(bundle, cookies)
        if not self.is_configured():
            logger.warning("[XHS] Not configured")
            return PlatformUploadResult(
                platform=self.platform_name,
                success=False,
                error="credentials not configured (no active session and no API key)",
            )
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
