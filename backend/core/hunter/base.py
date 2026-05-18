"""Hunter 基类 — 所有爬虫继承此类"""
from __future__ import annotations

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


class BaseHunter(ABC):
    @abstractmethod
    async def hunt(self, keywords: list[str] | None = None, limit: int = 20) -> list[RawSignal]:
        ...
