"""Reddit 热点爬虫"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from backend.core.hunter.base import BaseHunter, RawSignal, get_proxy

HIGH_EMOTION_SUBREDDITS: dict[str, list[str]] = {
    "loneliness": ["lonely", "depression", "socialskills", "introvert"],
    "anxiety": ["anxiety", "careerguidance", "GetMotivated"],
    "money_desire": ["sidehustle", "passive_income", "financialindependence"],
    "identity": ["mbti", "infj", "personalitytypes"],
    "escapism": ["books", "manga", "webtoons"],
    "ai_trends": ["artificial", "MachineLearning", "ChatGPT"],
}


class RedditHunter(BaseHunter):
    BASE_URL = "https://www.reddit.com"
    HEADERS = {"User-Agent": "NeuroTrendBot/1.0"}
    PROXY = get_proxy()

    async def hunt(
        self,
        keywords: Optional[list[str]] = None,
        limit: int = 20,
        subreddits: Optional[list[str]] = None,
        emotion_category: Optional[str] = None,
    ) -> list[RawSignal]:
        if subreddits:
            targets = subreddits
        elif emotion_category and emotion_category in HIGH_EMOTION_SUBREDDITS:
            targets = HIGH_EMOTION_SUBREDDITS[emotion_category]
        else:
            targets = [s for group in HIGH_EMOTION_SUBREDDITS.values() for s in group]

        signals: list[RawSignal] = []
        async with httpx.AsyncClient(
            headers=self.HEADERS, timeout=30.0, proxy=self.PROXY
        ) as client:
            for sub in targets[:5]:
                try:
                    resp = await client.get(
                        f"{self.BASE_URL}/r/{sub}/hot.json",
                        params={"limit": limit},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for post in data["data"]["children"]:
                        p = post["data"]
                        if p.get("stickied") or p.get("distinguished") == "moderator":
                            continue
                        signals.append(
                            RawSignal(
                                source="reddit",
                                title=p["title"],
                                content=p.get("selftext", "")[:1000],
                                url=f"https://reddit.com{p['permalink']}",
                                engagement_score=float(p["score"]) + float(p["num_comments"]) * 3,
                                raw_data={
                                    "subreddit": sub,
                                    "upvote_ratio": p["upvote_ratio"],
                                    "num_comments": p["num_comments"],
                                    "awards": p.get("total_awards_received", 0),
                                },
                            )
                        )
                    await asyncio.sleep(1.0)
                except httpx.HTTPStatusError as e:
                    print(f"[RedditHunter] HTTP {e.response.status_code} for r/{sub}")
                except Exception as e:
                    print(f"[RedditHunter] Error fetching r/{sub}: {e}")
        return sorted(signals, key=lambda x: x.engagement_score, reverse=True)
