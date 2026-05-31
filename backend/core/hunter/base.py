"""Hunter 基类 — 所有爬虫继承此类"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawSignal:
    source: str
    title: str
    content: str
    url: str
    engagement_score: float
    raw_data: dict[str, Any] = field(default_factory=dict)


def get_proxy() -> str | None:
    """获取代理地址（GFW 环境下 Reddit 需要走代理）"""
    return os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or "http://127.0.0.1:7890"


class BaseHunter(ABC):
    @abstractmethod
    async def hunt(self, keywords: list[str] | None = None, limit: int = 20) -> list[RawSignal]:
        ...
