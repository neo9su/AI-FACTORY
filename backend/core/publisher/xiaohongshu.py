from __future__ import annotations

import os
import logging
import json
from typing import Any, Dict
from anthropic import Anthropic

from backend.core.publisher.base import BasePublisher
from backend.models.trend import ContentProduct

logger = logging.getLogger(__name__)

class XiaohongshuPublisher(BasePublisher):
    """Xiaohong	hsu (小红书) style formatter."""

    def __init__(self, product: ContentProduct) -> None:
        super().__init__(product)
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def get_platform_name(self) -> str:
        return "xiaohongshu"

    async def format_post(self, content: str) -> Dict[str, Any]:
        """
        Transforms raw product content into an engaging Xiaohongshu post.
        """
        prompt = f"""
        You are a Xiaohongshu (小红书) influencer expert. 
        Your task is to transform the following product information into a viral, high-engagement Xiaohongshu post.

        PRODUCT INFORMATION:
        {content}

        REQUIREMENTS:
        1. TITLE: Create an irresistible, click-bait title (use emojis, e.g., '✨ 终于等到你！').
        2. BODY: Write in a friendly, 'sisterly' (姐妹们) or 'buddy' (家人们) conversational tone. 
           Focus on emotional resonance, pain points, and 'life hacks'.
           Use plenty of emojis throughout the text.
        3. HASHTAGS: Provide 5-10 trending Xiaohongshu hashtags (e.g., #小红书爆款 #好物分享).
        4. IMAGE PROMPTS: Suggest 3 specific prompts for Midjourney/Flux to create high-quality cover images that match this post's 
           vibe.

        OUTPUT FORMAT (Strict JSON):
        {{
            "title": "...",
            "body": "...",
            "hashtags": ["#tag1", "#tag2"],
            "image_prompts": ["prompt1", "prompt2", "prompt3"]
        }}
        """

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "text_plain"}
            )
            
            raw_text = response.content[0].text
            
            # Extraction
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()
                
            data = json.loads(raw_text)
            return {
                "title": data.get("title", ""),
                "body": data.get("body", ""),
                "hashtags": data.get("hashtags", []),
                "image_prompts": data.get("image_prompts", [])
            }
        except Exception as e:
            logger.error(f"Xiaohongshu formatting failed: {e}")
            raise e
