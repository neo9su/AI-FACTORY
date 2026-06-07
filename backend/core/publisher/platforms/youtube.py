"""YouTube Data API v3 client.

Uploads videos to YouTube using OAuth2 authentication.
Requires: google-api-python-client, google-auth-oauthlib
Env vars: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class YouTubeClient(PlatformClient):
    """YouTube Data API v3 client — OAuth2 with refresh token.

    Required env vars:
        YOUTUBE_CLIENT_ID
        YOUTUBE_CLIENT_SECRET
        YOUTUBE_REFRESH_TOKEN
    """

    platform_name = "youtube"

    def __init__(self) -> None:
        self.client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
        self.client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
        self.refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
        self._access_token: str | None = None

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    async def _refresh_access_token(self) -> str:
        """Exchange refresh token for a fresh access token."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                YOUTUBE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
        if not self.is_configured():
            logger.warning("[YouTube] Not configured")
            return PlatformUploadResult(
                platform="youtube",
                success=False,
                error="YOUTUBE_CLIENT_ID / YOUTUBE_REFRESH_TOKEN not set",
            )

        try:
            token = await self._refresh_access_token()
        except Exception as e:
            return PlatformUploadResult(
                platform="youtube",
                success=False,
                error=f"Failed to refresh token: {e}",
            )

        title = bundle.get("title", "AI Generated Video")[:100]
        description = bundle.get("caption", "")
        hashtags = bundle.get("hashtags", [])
        tag_str = " ".join(hashtags[:15])
        full_desc = f"{description}\n\n{tag_str}".strip()[:5000]

        metadata = {
            "snippet": {
                "title": title,
                "description": full_desc,
                "tags": hashtags[:15],
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        video_url = bundle.get("audio_url") or bundle.get("video_url", "")
        if not video_url:
            return PlatformUploadResult(
                platform="youtube",
                success=False,
                error="No video URL provided",
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/*",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Initiate resumable upload
                init_resp = await client.post(
                    YOUTUBE_UPLOAD_URL,
                    headers=headers,
                    json=metadata,
                )
                if init_resp.status_code != 200:
                    return PlatformUploadResult(
                        platform="youtube",
                        success=False,
                        error=f"YouTube init failed: {init_resp.status_code}",
                        raw_response=init_resp.json() if init_resp.text else {},
                    )

                upload_url = init_resp.headers.get("Location", "")
                if not upload_url:
                    return PlatformUploadResult(
                        platform="youtube",
                        success=False,
                        error="YouTube requires direct file upload. Use OAuth consent screen to authorize.",
                        raw_response={"note": "youtube requires file upload, not url-pull"},
                    )

                # Download video then upload
                video_resp = await client.get(video_url)
                if video_resp.status_code != 200:
                    return PlatformUploadResult(
                        platform="youtube",
                        success=False,
                        error=f"Failed to download video: {video_resp.status_code}",
                    )

                upload_headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "video/*",
                    "Content-Length": str(len(video_resp.content)),
                }

                upload_resp = await client.put(
                    upload_url, headers=upload_headers, content=video_resp.content,
                )

                if upload_resp.status_code in (200, 201):
                    data = upload_resp.json()
                    video_id = data.get("id", "")
                    return PlatformUploadResult(
                        platform="youtube",
                        success=True,
                        post_id=video_id,
                        post_url=f"https://www.youtube.com/watch?v={video_id}",
                        raw_response=data,
                    )
                else:
                    return PlatformUploadResult(
                        platform="youtube",
                        success=False,
                        error=f"YouTube upload failed: {upload_resp.status_code}",
                    )
        except Exception as e:
            logger.exception(f"[YouTube] Upload failed: {e}")
            return PlatformUploadResult(
                platform="youtube", success=False, error=str(e)
            )


__all__ = ["YouTubeClient"]
