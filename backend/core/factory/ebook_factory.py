"""AI 电子书工厂 — 根据商机报告自动生成结构化电子书内容"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.core.llm import llm_chat_async, llm_chat_json_async

logger = logging.getLogger(__name__)

EBOOK_OUTLINE_PROMPT = """\
你是一位畅销心理学/自我成长书籍的资深编辑，精通将互联网热点转化为读者愿意付费的电子书。

商机主题: {topic}
核心情绪: {emotions}
核心痛点: {pain_points}
目标受众: {audience}
付费触发点: {willingness_to_pay}

请生成一本针对该受众痛点的电子书完整大纲，必须返回纯 JSON（不要 markdown 代码块）:

{{
  "title": "吸引人的书名（含情绪钩子）",
  "subtitle": "副标题（强调价值主张）",
  "tagline": "一句话卖点（≤20字）",
  "target_audience": "目标读者描述",
  "price_suggestion": "$9.9",
  "total_pages": 35,
  "chapters": [
    {{
      "number": 1,
      "title": "章节标题",
      "hook": "开篇钩子（让读者产生共鸣的一句话）",
      "key_points": ["知识点1", "知识点2", "知识点3"],
      "emotional_arc": "本章情绪走向（痛苦→希望/认知→行动）",
      "word_count": 800
    }}
  ],
  "intro_sample": "书籍开头500字示例（能让读者产生共鸣立即想继续阅读的内容）",
  "marketing_angles": ["营销角度1", "营销角度2", "营销角度3"],
  "sales_page_headline": "销售页主标题"
}}

要求:
- 5-7 章，每章含具体可执行建议
- 章节标题要有情绪钩子，如"为什么你总是在凌晨3点刷手机"
- intro_sample 必须写满，真实可用
- 整体基调: 理解+共鸣+赋能，不说教
"""

CHAPTER_CONTENT_PROMPT = """\
你是专业的心理学/自我成长内容创作者。

书名: {title}
章节: 第{number}章 {chapter_title}
章节钩子: {hook}
核心知识点: {key_points}
情绪走向: {emotional_arc}
目标字数: {word_count}字

请写出完整的章节内容，要求:
1. 开篇用真实感强的场景描述引入（让读者觉得"这说的就是我"）
2. 用通俗易懂的语言解释心理学原理
3. 提供2-3个具体可操作的建议
4. 结尾用情感共鸣句收尾
5. 字数达到目标字数

直接输出章节正文，不要标题行。
"""


class EbookFactory:
    """AI 电子书自动生成工厂"""

    # Uses OpenAI-compatible API via backend.core.llm helpers

    async def generate_outline(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """根据商机报告生成电子书大纲"""
        topic = opportunity.get("topic", "")
        emotions = ", ".join(opportunity.get("core_emotions", []))
        pain_points = "; ".join(opportunity.get("core_pain_points", [])[:3])
        audience = opportunity.get("audience_profile", "18-35岁都市年轻人")
        willingness = opportunity.get("willingness_to_pay", "")

        prompt = EBOOK_OUTLINE_PROMPT.format(
            topic=topic,
            emotions=emotions,
            pain_points=pain_points,
            audience=audience,
            willingness_to_pay=willingness,
        )

        logger.info(f"[EbookFactory] Generating outline for: {topic[:40]}")
        data = await llm_chat_json_async(prompt, max_tokens=4096)
        return data

    async def generate_chapter(
        self,
        book_title: str,
        chapter: dict[str, Any],
    ) -> str:
        """生成单个章节正文"""
        prompt = CHAPTER_CONTENT_PROMPT.format(
            title=book_title,
            number=chapter.get("number", 1),
            chapter_title=chapter.get("title", ""),
            hook=chapter.get("hook", ""),
            key_points="\n".join(f"- {p}" for p in chapter.get("key_points", [])),
            emotional_arc=chapter.get("emotional_arc", ""),
            word_count=chapter.get("word_count", 800),
        )

        logger.info(f"[EbookFactory] Writing chapter {chapter.get('number')}: {chapter.get('title', '')[:30]}")
        content = await llm_chat_async(prompt, max_tokens=3000)
        return content

    async def generate_full_ebook(
        self,
        opportunity: dict[str, Any],
        chapters_to_write: int = 2,
    ) -> dict[str, Any]:
        """生成完整电子书（大纲 + 前N章正文）"""
        outline = await self.generate_outline(opportunity)
        chapters = outline.get("chapters", [])

        # 只生成前 N 章正文（节省 token，其余章节有大纲已足够展示）
        written_chapters = []
        for ch in chapters[:chapters_to_write]:
            content = await self.generate_chapter(outline.get("title", ""), ch)
            written_chapters.append({
                **ch,
                "content": content,
                "written": True,
            })

        # 其余章节保留大纲
        for ch in chapters[chapters_to_write:]:
            written_chapters.append({**ch, "written": False})

        return {
            **outline,
            "chapters": written_chapters,
            "product_type": "ebook",
            "status": "draft",
            "written_chapters_count": chapters_to_write,
        }
