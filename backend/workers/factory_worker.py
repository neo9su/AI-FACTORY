"""Content Factory 异步工作队列 — 将商机报告转化为内容产品"""
from __future__ import annotations

import logging
from typing import Any

from backend.core.factory.ebook_factory import EbookFactory
from backend.core.factory.personality_test_factory import PersonalityTestFactory
from backend.core.factory.video_script_factory import VideoScriptFactory
from backend.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def generate_content_product(
    ctx: dict[str, Any],
    product_id: str,
    opportunity_data: dict[str, Any],
    product_type: str,
) -> dict[str, Any]:
    """异步生成内容产品

    Args:
        ctx: ARQ worker context
        product_id: ContentProduct.id (需要更新状态)
        opportunity_data: OpportunityReport 的 dict 形式
        product_type: ebook | personality_test | short_video_scripts

    Returns:
        dict with keys: product_id, product_type, status, result
    """
    from backend.models.trend import ContentProduct
    from sqlalchemy import select

    logger.info(f"[FactoryWorker] Generating {product_type} for product {product_id}")

    # Step 1: 更新状态为 generating
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ContentProduct).where(ContentProduct.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            logger.error(f"[FactoryWorker] Product {product_id} not found")
            return {"product_id": product_id, "status": "failed", "error": "not found"}
        product.status = "generating"
        await session.commit()

    # Step 2: 调用对应 Factory
    try:
        if product_type == "ebook":
            factory = EbookFactory()
            content = await factory.generate_full_ebook(opportunity_data)
        elif product_type == "personality_test":
            factory = PersonalityTestFactory()
            content = await factory.generate_h5(opportunity_data)
        elif product_type == "short_video_scripts":
            factory = VideoScriptFactory()
            content = await factory.generate_scripts(opportunity_data)
        else:
            raise ValueError(f"Unknown product_type: {product_type}")

        # Step 3: Generate SD cover image (best-effort, non-blocking)
        cover_url = None
        try:
            from backend.core.image.sd_service import SDImageService
            sd = SDImageService()
            topic = opportunity_data.get("topic", "")
            emotions = opportunity_data.get("core_emotions", [])
            emotion_str = "、".join(emotions[:3]) if emotions else "情绪疗愈"
            prompt = (
                f"Chinese woman, emotional healing, {topic}, {emotion_str}, "
                "soft lighting, portrait, cinematic, 35mm film photography"
            )
            cover_path = await sd.generate_cover(
                prompt=prompt,
                product_id=product_id,
            )
            if cover_path:
                filename = cover_path.split("/")[-1] if "/" in cover_path else cover_path
                cover_url = f"/static/images/{filename}"
            logger.info(f"[FactoryWorker] SD cover generated: {cover_url}")
        except Exception as cover_err:
            logger.warning(f"[FactoryWorker] SD cover generation skipped: {cover_err}")

        # Attach cover URL to content dict for downstream use
        if cover_url and isinstance(content, dict):
            content["cover_image_url"] = cover_url

        # Step 4: 保存结果到 ContentProduct.meta
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentProduct).where(ContentProduct.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                product.status = "ready"
                product.title = content.get("title", "")
                product.meta = content
                await session.commit()
                logger.info(f"[FactoryWorker] {product_type} ready: {product_id}")

        return {"product_id": product_id, "product_type": product_type, "status": "ready"}

    except Exception as e:
        logger.exception(f"[FactoryWorker] Failed to generate {product_type}: {e}")
        # 更新为 failed
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentProduct).where(ContentProduct.id == product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                product.status = "failed"
                product.meta = {"error": str(e)}
                await session.commit()
        return {
            "product_id": product_id,
            "product_type": product_type,
            "status": "failed",
            "error": str(e),
        }
