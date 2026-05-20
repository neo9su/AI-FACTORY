"""SD Image Service — client for the GPU server SD API
Generates cover images for video scripts and ebooks.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

SD_API_URL = "http://10.190.0.222:7860"
IMAGE_OUTPUT_DIR = str(Path.home() / "autonomous-ai-factory/static/images")

COVER_PROMPT_TEMPLATE = """\
{topic}, emotional healing, cinematic portrait photography, \
soft warm lighting, shallow depth of field, young asian woman, peaceful expression, \
photorealistic, high quality, 4k
"""

NEGATIVE_PROMPT = (
    "ugly, blurry, bad anatomy, extra limbs, watermark, text, deformed, "
    "nsfw, cartoon, anime, low quality, overexposed"
)


class SDImageService:
    """Client for the Stable Diffusion GPU server."""

    def __init__(self, api_url: str = SD_API_URL) -> None:
        self.api_url = api_url
        Path(IMAGE_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    async def health_check(self) -> bool:
        """Check if the SD server is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.api_url}/")
                return r.status_code == 200
        except Exception:
            return False

    async def generate_cover(
        self,
        topic: str,
        emotions: list[str] | None = None,
        width: int = 512,
        height: int = 768,
        steps: int = 20,
        seed: int = -1,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate a cover image for a product.

        Returns:
            dict with keys: url, saved_path, prompt
        """
        emotion_str = ", ".join(emotions[:2]) if emotions else "emotional"
        prompt = COVER_PROMPT_TEMPLATE.format(topic=topic) + f", {emotion_str}"

        payload = {
            "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "steps": steps,
            "cfg_scale": 7.0,
            "width": width,
            "height": height,
            "seed": seed,
            "save_to_file": False,  # we'll save it ourselves
        }

        logger.info(f"[SDImageService] Generating cover for: {topic[:40]}")

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(f"{self.api_url}/sdapi/v1/txt2img", json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            raise RuntimeError(f"SD API call failed: {e}") from e

        b64 = data["images"][0]
        img_bytes = base64.b64decode(b64)

        fname = f"{product_id or uuid.uuid4().hex}_cover.png"
        out_path = str(Path(IMAGE_OUTPUT_DIR) / fname)
        with open(out_path, "wb") as f:
            f.write(img_bytes)

        url = f"/static/images/{fname}"
        logger.info(f"[SDImageService] Cover saved: {out_path}")

        return {
            "url": url,
            "saved_path": out_path,
            "prompt": prompt,
            "width": width,
            "height": height,
        }

    async def generate_batch(
        self,
        topics: list[str],
        emotions_list: list[list[str]] | None = None,
        product_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate multiple covers concurrently (max 3 at a time)."""
        semaphore = asyncio.Semaphore(3)

        async def _guarded(i: int) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self.generate_cover(
                        topic=topics[i],
                        emotions=emotions_list[i] if emotions_list else None,
                        product_id=product_ids[i] if product_ids else None,
                    )
                except Exception as e:
                    logger.warning(f"[SDImageService] Batch item {i} failed: {e}")
                    return {"error": str(e), "topic": topics[i]}

        tasks = [_guarded(i) for i in range(len(topics))]
        return await asyncio.gather(*tasks)
