"""TTS Worker — 异步将视频脚本 narration 合成为 WAV 配音"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AUDIO_OUTPUT_DIR = str(Path.home() / "autonomous-ai-factory/static/audio")


async def generate_tts_audio(
    ctx: dict[str, Any],
    product_id: str,
) -> dict[str, Any]:
    """异步生成视频脚本配音

    流程:
    1. 查询 ContentProduct，确认 product_type=short_video_scripts 且 status=ready
    2. 更新 tts_status=generating
    3. 遍历 meta.scripts 中 tts_suitable=True 的脚本
    4. 提取每个脚本的 narration 行
    5. 逐行调用 TTSService.synthesize_lines()
    6. 合并为完整 WAV
    7. 更新 tts_status=ready, tts_audio_urls=[{script_id, url}]
    """
    from backend.core.tts.tts_service import TTSService
    from backend.db.session import AsyncSessionLocal
    from backend.models.trend import ContentProduct
    from sqlalchemy import select

    logger.info(f"[TTSWorker] Starting TTS for product {product_id}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ContentProduct).where(ContentProduct.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            logger.error(f"[TTSWorker] Product {product_id} not found")
            return {"status": "failed", "error": "Product not found"}

        if product.product_type != "short_video_scripts":
            return {
                "status": "failed",
                "error": f"TTS only for short_video_scripts, got {product.product_type}",
            }

        if product.status != "ready":
            return {
                "status": "failed",
                "error": f"Product not ready, status={product.status}",
            }

        # 更新为 generating
        product.tts_status = "generating"
        await session.commit()

    # 在 session 外执行 TTS（避免长时间持有连接）
    tts = TTSService()
    audio_urls: list[dict[str, Any]] = []

    try:
        meta = product.meta or {}
        scripts = meta.get("scripts", [])

        for script in scripts:
            if not script.get("tts_suitable", False):
                continue

            script_id = script.get("id", 0)
            segments = script.get("script", [])
            lines = [
                seg.get("narration", "").strip()
                for seg in segments
                if seg.get("narration", "").strip()
            ]

            if not lines:
                continue

            logger.info(f"[TTSWorker] Synthesizing script {script_id}: {len(lines)} lines")

            # 逐行合成
            wav_paths = await tts.synthesize_lines(lines, product_id, script_index=script_id)

            if not wav_paths:
                continue

            # 合并为完整 WAV
            combined_path = str(
                Path(AUDIO_OUTPUT_DIR) / f"{product_id}_s{script_id}_combined.wav"
            )
            try:
                TTSService.concat_wavs(wav_paths, combined_path)
                audio_urls.append(
                    {
                        "script_id": script_id,
                        "script_title": script.get("title", ""),
                        "url": TTSService.wav_to_url(combined_path),
                        "lines_count": len(lines),
                    }
                )
                logger.info(f"[TTSWorker] Script {script_id} done: {combined_path}")
            except RuntimeError as e:
                logger.warning(f"[TTSWorker] concat failed for script {script_id}: {e}")

        # 更新 DB
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentProduct).where(ContentProduct.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                product.tts_status = "ready" if audio_urls else "failed"
                product.tts_audio_urls = audio_urls
                product.tts_error = None if audio_urls else "No audio generated"
                await session.commit()

        return {
            "status": "ready",
            "product_id": product_id,
            "scripts_synthesized": len(audio_urls),
            "audio_urls": audio_urls,
        }

    except Exception as e:
        logger.exception(f"[TTSWorker] TTS failed for {product_id}: {e}")
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentProduct).where(ContentProduct.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                product.tts_status = "failed"
                product.tts_error = str(e)[:500]
                await session.commit()
        return {"status": "failed", "error": str(e)}
