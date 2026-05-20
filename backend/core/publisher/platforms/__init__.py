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
