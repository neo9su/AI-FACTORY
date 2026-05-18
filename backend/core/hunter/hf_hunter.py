"""HuggingFace 热门模型趋势 Hunter — 抓取 AI 模型新趋势"""
from __future__ import annotations

from typing import Optional

import httpx

from backend.core.hunter.base import BaseHunter, RawSignal

# HuggingFace Trending Models API (public, no auth needed)
HF_API_URL = "https://huggingface.co/api/models"

# 高价値任务类型（这些最容易找到商机）
HIGH_VALUE_TASKS = [
    "text-generation",
    "text-to-image",
    "text-to-speech",
    "image-to-text",
    "text-to-video",
    "automatic-speech-recognition",
]


class HFHunter(BaseHunter):
    """HuggingFace 热门模型 Hunter"""

    CATEGORY = "ai_trends"

    async def hunt(
        self,
        keywords: Optional[list[str]] = None,
        limit: int = 20,
    ) -> list[RawSignal]:
        """抓取 HuggingFace 热门模型趋势"""
        signals: list[RawSignal] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for task in HIGH_VALUE_TASKS[:4]:
                try:
                    resp = await client.get(
                        HF_API_URL,
                        params={
                            "pipeline_tag": task,
                            "sort": "trending",
                            "limit": 10,
                        },
                    )
                    resp.raise_for_status()
                    models = resp.json()

                    for m in models:
                        model_id = m.get("modelId", "")
                        downloads = m.get("downloads", 0) or 0
                        likes = m.get("likes", 0) or 0
                        tags = m.get("tags", [])

                        signals.append(
                            RawSignal(
                                source="huggingface",
                                title=f"[{task}] {model_id}",
                                content=f"Downloads: {downloads:,} | Likes: {likes} | Tags: {', '.join(tags[:5])}",
                                url=f"https://huggingface.co/{model_id}",
                                engagement_score=float(likes) * 10 + float(downloads) / 1000,
                                raw_data={
                                    "model_id": model_id,
                                    "task": task,
                                    "downloads": downloads,
                                    "likes": likes,
                                    "tags": tags[:10],
                                    "category": "ai_trends",
                                },
                            )
                        )
                except Exception as e:
                    print(f"[HFHunter] {task}: {e}")

        return sorted(signals, key=lambda x: x.engagement_score, reverse=True)[:limit]
