"""Product Hunt 趋势爬虫"""
from __future__ import annotations

from typing import Optional

import httpx

from backend.core.hunter.base import BaseHunter, RawSignal

PRODUCTHUNT_GQL = "https://api.producthunt.com/v2/api/graphql"
AI_QUERY = """
query GetAIPosts {
  posts(first: 20, order: VOTES, topic: "artificial-intelligence") {
    edges { node { id name tagline description votesCount commentsCount website topics { edges { node { name } } } } }
  }
}
"""


class ProductHuntHunter(BaseHunter):
    def __init__(self, api_token: Optional[str] = None) -> None:
        self.api_token = api_token

    async def hunt(
        self,
        keywords: Optional[list[str]] = None,
        limit: int = 20,
        ai_only: bool = True,
    ) -> list[RawSignal]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        signals: list[RawSignal] = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    PRODUCTHUNT_GQL,
                    json={"query": AI_QUERY},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                for edge in data.get("data", {}).get("posts", {}).get("edges", [])[:limit]:
                    n = edge["node"]
                    topics = [e["node"]["name"] for e in n.get("topics", {}).get("edges", [])]
                    signals.append(
                        RawSignal(
                            source="product_hunt",
                            title=n["name"],
                            content=f"{n['tagline']}\n{n.get('description') or ''}",
                            url=n.get("website", ""),
                            engagement_score=float(n["votesCount"]) + float(n["commentsCount"]) * 2,
                            raw_data={
                                "votes": n["votesCount"],
                                "comments": n["commentsCount"],
                                "topics": topics,
                            },
                        )
                    )
        except Exception as e:
            print(f"[ProductHuntHunter] Error: {e}")
        return sorted(signals, key=lambda x: x.engagement_score, reverse=True)
