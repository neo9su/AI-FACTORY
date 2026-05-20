"""Phase 5D — QR login client registry."""
from __future__ import annotations

from backend.core.publisher.login.base import LoginResult, QRLoginClient, QRLoginSession
from backend.core.publisher.login.douyin_login import DouyinLoginClient
from backend.core.publisher.login.xiaohongshu_login import XiaohongshuLoginClient

LOGIN_REGISTRY: dict[str, type[QRLoginClient]] = {
    "xiaohongshu": XiaohongshuLoginClient,
    "douyin": DouyinLoginClient,
}


def get_login_client(platform: str) -> QRLoginClient:
    """Return a fresh login client instance for the given platform."""
    cls = LOGIN_REGISTRY.get(platform)
    if not cls:
        raise ValueError(f"No login client for platform: {platform}. Supported: {list(LOGIN_REGISTRY)}")
    return cls()


__all__ = [
    "QRLoginClient",
    "QRLoginSession",
    "LoginResult",
    "XiaohongshuLoginClient",
    "DouyinLoginClient",
    "LOGIN_REGISTRY",
    "get_login_client",
]
