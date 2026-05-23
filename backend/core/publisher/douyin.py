from __future__ import annotations

import os
import logging
import json
from typing import Any, Dict
from anthropic import Anthropic

from backend.core.publisher.base import BasePublisher
from backend.models.trend import ContentProduct

logger = logging.getLogger(__name__)

class DouyinPublisher(BasePublisher):
    """Douyin (抖音) style formatter."""

    def __init__(self, product: ContentProduct) -> None:
        super().__init__(product)
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def get_platform_name(self) -> str:
        return "douyin"

    async def format_post(self, content: str) -> Dict[str, Any]:
        """
        Transforms raw product content into a high-retention Douyin description.
        Focuses on:
        - Hook (the first 3 seconds)
        - Value proposition (what's in it for the viewer)
        - Call to action (CTA)
        """
        prompt = f"""
        You are a Douyin (抖音) viral video content creator. 
        Your task is to transform the following product information into a high-retention, short-form video description.

        PRODUCT INFORMATION:
        {content}

        REQUIREMENTS:
        1. DESCRIPTION: Write a punchy, high-energy description. 
           Start with a powerful 'Hook' (e.g., '千万别买... 除非你...', '这真的绝了!').
           Keep it short and fast-paced.
        2. HASHTAGS: Provide 3-5 trending Douyin hashtags (e.g., #抖音热门 #好物推荐).
        3. COVER TEXT: Suggest a short, impactful text overlay for the video cover (e.1. '震惊!').
        4. TIMING: Recommend the best time of day to post (e.g., '18:00 - 20:00').

        OUTPUT FORMAT (Strict JSON):
        {{
            "description": "...",
            "hashtags": ["#tag1", "#tag2"],
            "cover_text": "...",
            "best_time": "..."
        }}
        """

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "text_plain"}
            )
            
            raw_text = response.content[0].text
            
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()
                
            data = json.loads(raw_text)
            return {
                "description": data.get("description", ""),
                "hashtrag_list": data.get("hashtags", []), # Note: keys should be consistent with logic
                "cover_text": data.get("cover_text", ""),
                "best_time": data.get("best_time", "")
            }
        except Exception as e:
            logger.error(f"Douyin formatting failed: {e}")
            raise e
