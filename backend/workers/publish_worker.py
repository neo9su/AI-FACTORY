from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import AsyncSessionLocal
from backend.models.publish import PublishTask
from backend.models.trend import ContentProduct
from backend.core.publisher import XiaohongshuPublisher, DouyinPublisher

logger = logging.getLogger(__name__)

async def process_publish_job(ctx: dict[str, Any], task_id: str) -> None:
    """
    ARQ worker function to generate a platform-optimized publishing package.
    """
    async with AsyncSessionLocal() as db:
        # 1. Fetch Task
        result = await db.execute(select(PublishTask).where(PublishTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            logger.error(f"PublishTask {task_id} not found")
            return

        task.status = "packaging"
        await db.commit()

        try:
            # 2. Fetch Product
            prod_result = await db.execute(
                select(ContentProduct).where(ContentProduct.id == task.product_id)
            )
            product = prod_result.scalar_one_or_none()
            if not product:
                raise ValueError(f"ContentProduct {task.product_id} not found")

            # 3. Identify Publisher
            if task.platform == "xiaohongshu":
                publisher = XiaohongshuPublisher(product)
            elif task.platform == "douyin":
                publisher = DouyinPublisher(product)
            else:
                raise ValueError(f"Unsupported platform: {task.platform}")

            # 4. Generate Package
            content_summary = ""
            if product.product_type == "video_script":
                scripts = product.meta.get("scripts", [])
                content_summary = "\n".join([f"Scene {i+1}: {s}" for i, s in enumerate(scripts)])
            elif product.product_type == "ebook":
                chapters = product.meta.get("chapters", [])
                content_summary = "\n".join(chapters)
            else:
                content_summary = product.title

            logger.info(f"Generating package for {task.platform} (Product: {product.id})")
            package = await publisher.format_post(content_summary)

            # 5. Update Task
            task.publish_package = package
            task.status = "ready"
            await db.commit()
            logger.info(f"Publish package ready for {task.platform} task {task_id}")

        except Exception as e:
            logger.error(f"Publish task {task_id} failed: {async_exception_info(e)}")
            task.status = "failed"
            task.error_log = str(e)
            await db.commit()
            raise e

def async_exception_info(e: Exception) -> str:
    import traceback
    return traceback.format_exc()
