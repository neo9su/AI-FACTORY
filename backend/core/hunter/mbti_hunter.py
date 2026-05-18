"""MBTI & 人格心理专项 Hunter — 高情绪密度内容"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from backend.core.hunter.base import BaseHunter, RawSignal

MBTI_SUBREDDITS = [
    "mbti", "infj", "infp", "intj", "entp",
    "personalitytypes", "psychology", "LifeAdvice",
    "raisedbynarcissists", "socialskills",
]

MBTI_KEYWORDS = [
    "personality type", "why am I like this",
    "social anxiety", "attachment style", "love language",
    "narcissist", "introvert struggles",
]


class MBTIHunter(BaseHunter):
    """专注人格/心理领域的专项 Hunter"""

    BASE_URL = "https://www.reddit.com"
    HEADERS = {"User-Agent": "NeuroTrendBot/1.0"}
    CATEGORY = "identity"  # 对应 EmotionType 分类

    async def hunt(
        self,
        keywords: Optional[list[str]] = None,
        limit: int = 20,
    ) -> list[RawSignal]:
        """爬取 MBTI/人格心理类热门内容"""
        signals: list[RawSignal] = []

        async with httpx.AsyncClient(headers=self.HEADERS, timeout=30.0) as client:
            # 1. 爬取热门 subreddits
            for sub in MBTI_SUBREDDITS[:6]:
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
                                source="reddit_mbti",
                                title=p["title"],
                                content=p.get("selftext", "")[:1000],
                                url=f"https://reddit.com{p['permalink']}",
                                engagement_score=float(p["score"]) + float(p["num_comments"]) * 3,
                                raw_data={
                                    "subreddit": sub,
                                    "category": "identity",
                                    "upvote_ratio": p.get("upvote_ratio", 0),
                                    "num_comments": p["num_comments"],
                                },
                            )
                        )
                    await asyncio.sleep(1)
                except Exception as e:
                    # 网络限制时优雅降级
                    print(f"[MBTIHunter] {sub}: {e}")

            # 2. 关键词搜索
            kw_list = keywords or MBTI_KEYWORDS
            for kw in kw_list[:3]:
                try:
                    resp = await client.get(
                        f"{self.BASE_URL}/r/mbti/search.json",
                        params={"q": kw, "sort": "top", "t": "week", "limit": limit},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for post in data["data"]["children"]:
                        p = post["data"]
                        if p.get("stickied") or p.get("distinguished") == "moderator":
                            continue
                        signals.append(
                            RawSignal(
                                source="reddit_mbti",
                                title=p["title"],
                                content=p.get("selftext", "")[:1000],
                                url=f"https://reddit.com{p['permalink']}",
                                engagement_score=float(p["score"]) + float(p["num_comments"]) * 3,
                                raw_data={
                                    "subreddit": p.get("subreddit", "mbti"),
                                    "category": "identity",
                                    "keyword": kw,
                                    "upvote_ratio": p.get("upvote_ratio", 0),
                                    "num_comments": p["num_comments"],
                                },
                            )
                        )
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"[MBTIHunter] keyword '{kw}': {e}")

        return sorted(signals, key=lambda x: x.engagement_score, reverse=True)[:limit]
