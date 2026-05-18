"""Brain 情绪分析引擎"""

import json
import logging
from typing import Optional

from anthropic import Anthropic

from backend.core.brain.prompts import EMOTION_ANALYSIS_PROMPT
from backend.core.hunter.base import RawSignal

logger = logging.getLogger(__name__)


class EmotionAnalyzer:
    BATCH_MODEL = "claude-haiku-4-5"
    SINGLE_MODEL = "claude-sonnet-4-5"

    def __init__(self, model: Optional[str] = None) -> None:
        self.client = Anthropic()
        self.model = model or self.BATCH_MODEL

    async def analyze(self, signal: RawSignal) -> dict:
        content = f"标题：{signal.title}\n内容：{signal.content[:800]}"
        prompt = EMOTION_ANALYSIS_PROMPT.format(
            content=content,
            source=signal.source,
            engagement=f"互动分数: {signal.engagement_score:.0f}",
        )
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text.strip()
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == 0:
                return {"error": "no_json", "raw": response_text[:200]}
            return json.loads(response_text[start:end])
        except json.JSONDecodeError as e:
            logger.error(f"[EmotionAnalyzer] JSON parse error: {e}")
            return {"error": "parse_failed"}
        except Exception as e:
            logger.error(f"[EmotionAnalyzer] Error: {e}")
            return {"error": "api_error", "message": str(e)}

    async def batch_analyze(
        self, signals: list[RawSignal], top_n: int = 10
    ) -> list[tuple[RawSignal, dict]]:
        results: list[tuple[RawSignal, dict]] = []
        top_signals = sorted(
            signals, key=lambda x: x.engagement_score, reverse=True
        )[:top_n]
        for i, signal in enumerate(top_signals):
            logger.info(
                f"[Brain] 分析 {i + 1}/{len(top_signals)}: {signal.title[:50]}..."
            )
            result = await self.analyze(signal)
            results.append((signal, result))
        return results
