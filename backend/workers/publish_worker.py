"""ARQ worker for async publish job processing."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from backend.core.publisher.publisher_service import PublisherService
from backend.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ["douyin", "xiaohongshu", "tiktok"]


async def process_publish_job(
    ctx: dict[str, Any],
    publish_job_id: str,
) -> dict[str, Any]:
    """ARQ worker: package a ContentProduct into a publish bundle.

    Args:
        ctx: ARQ worker context
        publish_job_id: PublishJob.id

    Returns:
        dict with status and bundle_path
    """
    from backend.models.publish import PublishJob
    from backend.models.trend import ContentProduct

    logger.info(f"[PublishWorker] Processing publish job {publish_job_id}")

    async with AsyncSessionLocal() as db:
        # Load publish job
        result = await db.execute(
            select(PublishJob).where(PublishJob.id == publish_job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            return {"status": "failed", "error": "job not found"}

        # Load product
        result2 = await db.execute(
            select(ContentProduct).where(ContentProduct.id == job.product_id)
        )
        product = result2.scalar_one_or_none()
        if not product:
            job.status = "failed"
            job.error_msg = "product not found"
            await db.commit()
            return {"status": "failed", "error": "product not found"}

        # Update status to packaging
        job.status = "packaging"
        await db.commit()

        try:
            service = PublisherService()
            bundle = service.build_bundle(
                product_id=str(product.id),
                product_type=product.product_type,
                product_meta=product.meta or {},
                platform=job.platform,
                tts_audio_urls=product.tts_audio_urls,
                cover_image_url=_get_cover_url(product),
            )
            bundle_path = service.save_bundle(
                product_id=str(product.id),
                platform=job.platform,
                bundle=bundle,
            )

            job.status = "ready"
            job.bundle_path = bundle_path
            job.bundle_data = bundle
            await db.commit()

            logger.info(f"[PublishWorker] Job {publish_job_id} ready: {bundle_path}")

            # --- Phase 5C: upload to platform ---
            job.status = "uploading"
            await db.commit()

            try:
                upload_result = await service.upload_to_platform(
                    platform=job.platform,
                    bundle=bundle,
                )
                job.upload_result = {
                    "success": upload_result.success,
                    "post_id": upload_result.post_id,
                    "post_url": upload_result.post_url,
                    "error": upload_result.error,
                }
                if upload_result.success:
                    job.status = "uploaded"
                    job.post_id = upload_result.post_id
                    job.post_url = upload_result.post_url
                    logger.info(
                        f"[PublishWorker] Uploaded to {job.platform}: "
                        f"post_id={upload_result.post_id}"
                    )
                else:
                    job.status = "upload_failed"
                    logger.warning(
                        f"[PublishWorker] Upload to {job.platform} failed: "
                        f"{upload_result.error}"
                    )
            except Exception as upload_err:
                logger.exception(f"[PublishWorker] Upload exception: {upload_err}")
                job.status = "upload_failed"
                job.upload_result = {"success": False, "error": str(upload_err)}

            await db.commit()
            return {
                "status": job.status,
                "publish_job_id": publish_job_id,
                "bundle_path": bundle_path,
            }

        except Exception as e:
            logger.exception(f"[PublishWorker] Job {publish_job_id} failed: {e}")
            job.status = "failed"
            job.error_msg = str(e)
            await db.commit()
            return {"status": "failed", "error": str(e)}


def _get_cover_url(product: Any) -> str | None:
    """Extract cover image URL from product meta."""
    meta = product.meta or {}
    # Check common locations
    return (
        meta.get("cover_image_url")
        or meta.get("cover_url")
        or (
            product.content_url
            if product.content_url and ".png" in (product.content_url or "")
            else None
        )
    )
