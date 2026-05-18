"""快速测试：抓取 r/mbti 前 3 条热帖"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")
from backend.core.hunter.reddit_hunter import RedditHunter


async def main() -> None:
    hunter = RedditHunter()
    print("🔍 正在抓取 r/mbti 热帖...")
    signals = await hunter.hunt(subreddits=["Python"], limit=3)
    print(f"✅ 共获取 {len(signals)} 条信号\n")
    for i, sig in enumerate(signals[:3], 1):
        print(f"[{i}] {sig.title[:60]}...")
        print(f"     engagement_score={sig.engagement_score:.0f}  | r/{sig.raw_data['subreddit']}")
        print(f"     url={sig.url}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
