from backend.core.publisher.platforms.base import PlatformClient, PlatformUploadResult
from backend.core.publisher.platforms.douyin import DouyinClient
from backend.core.publisher.platforms.xiaohongshu import XiaohongshuClient
from backend.core.publisher.platforms.tiktok import TikTokClient
from backend.core.publisher.platforms.youtube import YouTubeClient
from backend.core.publisher.platforms.bilibili import BilibiliClient
from backend.core.publisher.platforms.kuaishou import KuaishouClient

PLATFORM_REGISTRY: dict[str, type[PlatformClient]] = {
    "douyin": DouyinClient,
    "xiaohongshu": XiaohongshuClient,
    "tiktok": TikTokClient,
    "youtube": YouTubeClient,
    "bilibili": BilibiliClient,
    "kuaishou": KuaishouClient,
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
