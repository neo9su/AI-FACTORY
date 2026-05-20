# /Users/susunxin/autonomous-ai-factory/backend/core/publisher/platforms/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

@dataclass
class PlatformUploadResult:
    platform: str
    success: bool
    post_id: str | None = None
    post_url: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

class PlatformClient(ABC):
    platform_name: str
    @abstractmethod
    async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult: ...
    @abstractmethod
    def is_configured(self) -> bool: ...
