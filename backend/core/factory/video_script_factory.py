"""AI 情绪短视频脚本生成工厂 — 生成适合抖音/TikTok 的情绪共鸣短视频脚本"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

VIDEO_SCRIPT_PROMPT = """\
你是一位在抖音/TikTok 拥有百万粉丝的情绪疗愈类短视频创作者，精通用30秒视频触动人心。

商机主题: {topic}
核心情绪: {emotions}
核心痛点: {pain_points}
目标受众: {audience}
营销钩子: {hook_lines}
爆点公式: {viral_formula}

请生成5个短视频脚本方案，必须返回纯 JSON（不要 markdown 代码块）:

{{
  "series_concept": "系列视频概念（一句话定位这套视频的核心价值）",
  "scripts": [
    {{
      "id": 1,
      "title": "视频标题（抖音风格，含情绪词）",
      "hook_line": "开场钩子（前3秒必须说的一句话，让人不划走）",
      "duration_seconds": 45,
      "format": "口播|情景剧|图文|vlog",
      "emotional_arc": "共情→共鸣→升华",
      "script": [
        {{
          "timestamp": "0-3s",
          "visual": "画面描述",
          "narration": "旁白/对话文字（可直接读的文案）",
          "emotion": "此刻情绪氛围"
        }}
      ],
      "caption": "视频文案（发布时的配文，含话题标签）",
      "hashtags": ["#话题1", "#话题2", "#话题3"],
      "expected_emotion": "用户看完后的情绪（被治愈/被激励/想分享）",
      "viral_potential": 8.5,
      "tts_suitable": true,
      "bgm_style": "轻音乐/钢琴曲/Lo-fi"
    }}
  ],
  "posting_strategy": {{
    "best_time": "晚上9-11点",
    "frequency": "每天1条，连发7天",
    "platform_priority": ["抖音", "小红书", "TikTok"],
    "growth_tactic": "增长策略说明"
  }},
  "monetization": {{
    "method": "引流变现方式",
    "cta": "行动号召文案",
    "estimated_views": "预估播放量范围"
  }}
}}

要求:
- 5个脚本涵盖不同格式（至少包含: 口播1个、情景剧1个、图文1个）
- script 数组中每个片段都要写具体的 narration 文字（可直接配音的）
- 每个脚本至少5个时间段
- hook_line 要有"停止刷手机"的力量
- tts_suitable=true 的脚本要写得更口语化
"""


class VideoScriptFactory:
    """AI 情绪短视频脚本生成工厂"""

    MODEL = "claude-sonnet-4-5"

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic()

    async def generate_scripts(
        self, opportunity: dict[str, Any]
    ) -> dict[str, Any]:
        """根据商机报告生成短视频脚本方案"""
        topic = opportunity.get("topic", "")
        emotions = ", ".join(opportunity.get("core_emotions", []))
        pain_points = "; ".join(opportunity.get("core_pain_points", [])[:3])
        audience = opportunity.get("audience_profile", "年轻人")
        hook_lines = "; ".join((opportunity.get("hook_lines") or [])[:2])
        viral = opportunity.get("viral_formula", "")

        prompt = VIDEO_SCRIPT_PROMPT.format(
            topic=topic,
            emotions=emotions,
            pain_points=pain_points,
            audience=audience,
            hook_lines=hook_lines,
            viral_formula=viral,
        )

        logger.info(f"[VideoScriptFactory] Generating scripts for: {topic[:40]}")
        message = await self._client.messages.create(
            model=self.MODEL,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = json.loads(raw)

        return {
            "product_type": "short_video_scripts",
            "title": f"{topic} — 短视频脚本系列",
            "series_concept": data.get("series_concept", ""),
            "scripts": data.get("scripts", []),
            "posting_strategy": data.get("posting_strategy", {}),
            "monetization": data.get("monetization", {}),
            "scripts_count": len(data.get("scripts", [])),
            "status": "ready",
        }

    async def generate_tts_ready_script(
        self, script: dict[str, Any]
    ) -> str:
        """将脚本转为 TTS 就绪的纯文字版本（适合 CosyVoice2 配音）"""
        if not script.get("tts_suitable"):
            return ""
        lines = []
        for seg in script.get("script", []):
            narration = seg.get("narration", "").strip()
            if narration:
                lines.append(narration)
        return "\n".join(lines)
