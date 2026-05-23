from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict
from backend.models.trend import ContentProduct

class BasePublisher(ABC):
    """Base class for all platform-specific publishers."""

    def __init__(self, product: ContentProduct) -> None:
        self.product = product

    @abstractmethod
    async def format_post(self, content: str) -> Dict[str, Any]:
        """
        Format the product content into a platform-specific post package.
        Returns a dict containing:
        - title: string
        - body: string
        - hashtags: list[str]
        - image_prompts: list[str]
        """
        pass

    @abstractmethod
    async def get_platform_name(self) -> str:
        """Return the platform identifier (e.g., 'xiaohongshu')."""
        pass

    async def get_product_context(self) -> str:
        """Helper to get a summary context of the product for the LLM."""
        if self.product.product_type == "video_script":
            return f"Video Script Title: {self.product.title}. Content: {self.product.meta.get('scripts', [])}"
        elif self.product.product_type == "ebook":
            return f"Ebook Title: {self.product.title}. Chapters: {self.product.meta.get('chapters', [])}"
        return f"Product: {self.product.title}"
