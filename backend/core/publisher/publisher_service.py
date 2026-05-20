"""Platform-specific publish bundle builder.

Packages a ContentProduct into a platform-optimized bundle:
- Selects best script based on viral_potential score
- Formats caption with hashtags per platform style
- References TTS audio URL and SD cover image URL
- Saves bundle.json to static/publish/<product_id>/<platform>/
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.core.publisher.platforms.base import PlatformUploadResult

PLATFORM_HASHTAG_LIMITS = {
    "douyin": 5,        # 抖音 recommend 3-5 tags
    "xiaohongshu": 10,  # 小红书 supports many tags
    "tiktok": 8,        # TikTok 5-8 tags
}

PLATFORM_CAPTION_LIMITS = {
    "douyin": 500,
    "xiaohongshu": 1000,
    "tiktok": 300,
}


class PublisherService:
    """Packages ContentProduct data into platform-specific publish bundles."""

    def __init__(self, static_dir: Path | None = None) -> None:
        self.static_dir = static_dir or (Path.home() / "autonomous-ai-factory/static")

    def build_bundle(
        self,
        product_id: str,
        product_type: str,
        product_meta: dict[str, Any],
        platform: str,
        tts_audio_urls: list[dict] | None = None,
        cover_image_url: str | None = None,
    ) -> dict[str, Any]:
        """Build a publish bundle for a specific platform.

        Args:
            product_id: ContentProduct UUID
            product_type: ebook | personality_test | short_video_scripts
            product_meta: ContentProduct.meta dict (AI-generated content)
            platform: douyin | xiaohongshu | tiktok
            tts_audio_urls: list of {script_id, url, duration_hint}
            cover_image_url: URL to SD-generated cover image

        Returns:
            Platform-optimized publish bundle dict
        """
        if product_type == "short_video_scripts":
            return self._bundle_video_scripts(
                product_id, product_meta, platform, tts_audio_urls, cover_image_url
            )
        elif product_type == "ebook":
            return self._bundle_ebook(
                product_id, product_meta, platform, cover_image_url
            )
        elif product_type == "personality_test":
            return self._bundle_personality_test(
                product_id, product_meta, platform, cover_image_url
            )
        else:
            raise ValueError(f"Unknown product_type: {product_type}")

    def _bundle_video_scripts(
        self,
        product_id: str,
        meta: dict[str, Any],
        platform: str,
        tts_audio_urls: list[dict] | None,
        cover_image_url: str | None,
    ) -> dict[str, Any]:
        """Bundle video scripts — picks best script by viral_potential."""
        scripts = meta.get("scripts", [])
        if not scripts:
            raise ValueError("No scripts found in product meta")

        # Pick script with highest viral_potential
        best_script = max(scripts, key=lambda s: s.get("viral_potential", 0))
        script_id = best_script.get("id", 1)

        # Find matching TTS audio
        audio_url = None
        if tts_audio_urls:
            for item in tts_audio_urls:
                if str(item.get("script_id")) == str(script_id):
                    audio_url = item.get("url")
                    break
            if not audio_url and tts_audio_urls:
                audio_url = tts_audio_urls[0].get("url")

        # Platform-specific hashtags
        hashtags = best_script.get("hashtags", [])
        limit = PLATFORM_HASHTAG_LIMITS.get(platform, 5)
        hashtags = hashtags[:limit]

        # Build caption
        caption = best_script.get("caption", "")
        cap_limit = PLATFORM_CAPTION_LIMITS.get(platform, 500)
        if len(caption) > cap_limit:
            caption = caption[: cap_limit - 3] + "..."

        # Full narration text (for manual posting reference)
        narration_parts = [
            seg.get("narration", "") for seg in best_script.get("script", [])
        ]
        narration_text = "\n".join(filter(None, narration_parts))

        return {
            "platform": platform,
            "product_id": product_id,
            "product_type": "short_video_scripts",
            "selected_script_id": script_id,
            "title": best_script.get("title", ""),
            "hook_line": best_script.get("hook_line", ""),
            "caption": caption,
            "hashtags": hashtags,
            "duration_seconds": best_script.get("duration_seconds", 45),
            "format": best_script.get("format", "口播"),
            "bgm_style": best_script.get("bgm_style", "轻音乐"),
            "narration_text": narration_text,
            "audio_url": audio_url,
            "cover_image_url": cover_image_url,
            "posting_strategy": meta.get("posting_strategy", {}),
            "viral_potential": best_script.get("viral_potential", 0),
            "series_concept": meta.get("series_concept", ""),
        }

    def _bundle_ebook(
        self,
        product_id: str,
        meta: dict[str, Any],
        platform: str,
        cover_image_url: str | None,
    ) -> dict[str, Any]:
        """Bundle ebook for social media promotion post."""
        marketing_angles = meta.get("marketing_angles", [])
        limit = PLATFORM_HASHTAG_LIMITS.get(platform, 5)

        # Build hashtags from title words
        title = meta.get("title", "")
        hashtags = [f"#{w}" for w in title.split()[:3] if w]
        hashtags += ["#电子书", "#自我成长", "#心理学"]
        hashtags = hashtags[:limit]

        caption = f"{meta.get('sales_page_headline', title)}\n\n{meta.get('tagline', '')}"
        if marketing_angles:
            caption += "\n\n" + "\n".join(f"✅ {a}" for a in marketing_angles[:3])
        caption += f"\n\n👇 评论区留言「{meta.get('price_suggestion', '$9.9')}」获取"

        return {
            "platform": platform,
            "product_id": product_id,
            "product_type": "ebook",
            "title": meta.get("title", ""),
            "subtitle": meta.get("subtitle", ""),
            "tagline": meta.get("tagline", ""),
            "caption": caption[: PLATFORM_CAPTION_LIMITS.get(platform, 500)],
            "hashtags": hashtags,
            "cover_image_url": cover_image_url,
            "price_suggestion": meta.get("price_suggestion", "$9.9"),
            "intro_sample": meta.get("intro_sample", "")[:200],
            "audio_url": None,
        }

    def _bundle_personality_test(
        self,
        product_id: str,
        meta: dict[str, Any],
        platform: str,
        cover_image_url: str | None,
    ) -> dict[str, Any]:
        """Bundle personality test as interactive content teaser."""
        limit = PLATFORM_HASHTAG_LIMITS.get(platform, 5)
        test_name = meta.get("test_name", "心理测试")
        hashtags = [f"#{test_name}", "#MBTI", "#心理测试", "#性格测试", "#自我探索"][:limit]

        caption = f"🧠 {test_name}\n\n{meta.get('description', '')}"
        caption += "\n\n👇 点击主页链接免费测试"

        return {
            "platform": platform,
            "product_id": product_id,
            "product_type": "personality_test",
            "title": test_name,
            "caption": caption[: PLATFORM_CAPTION_LIMITS.get(platform, 500)],
            "hashtags": hashtags,
            "cover_image_url": cover_image_url,
            "audio_url": None,
        }

    def save_bundle(
        self, product_id: str, platform: str, bundle: dict[str, Any]
    ) -> str:
        """Save bundle JSON to static dir and return relative URL path."""
        output_dir = self.static_dir / "publish" / product_id / platform
        output_dir.mkdir(parents=True, exist_ok=True)

        bundle_path = output_dir / "bundle.json"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))

        relative_url = f"/static/publish/{product_id}/{platform}/bundle.json"
        logger.info(f"[Publisher] Bundle saved to {bundle_path}")
        return relative_url

    async def upload_to_platform(
        self,
        platform: str,
        bundle: dict[str, Any],
    ) -> "PlatformUploadResult":
        """Upload a bundle to the specified platform.

        Args:
            platform: "douyin" | "xiaohongshu" | "tiktok"
            bundle: The platform-specific bundle dict

        Returns:
            PlatformUploadResult
        """
        from backend.core.publisher.platforms import get_platform_client

        client = get_platform_client(platform)
        logger.info(
            f"[Publisher] Uploading to {platform} "
            f"(configured={client.is_configured()})"
        )
        result = await client.upload(bundle)
        return result
