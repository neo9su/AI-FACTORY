"""Strategist 商机生成器 — 将情绪数据转化为商业机会"""
from __future__ import annotations

import json
import logging

from backend.core.brain.prompts import OPPORTUNITY_GENERATION_PROMPT
from backend.core.llm import llm_chat

logger = logging.getLogger(__name__)


class OpportunityGenerator:
    """商机生成器，调用 LLM 将情绪分析转化为结构化商业报告"""

    def __init__(self) -> None:
        pass

    async def generate(self, topic: str, emotion_analysis: dict) -> dict:
        """生成完整商业机会报告"""
        prompt = OPPORTUNITY_GENERATION_PROMPT.format(
            topic=topic,
            emotion_analysis=json.dumps(emotion_analysis, ensure_ascii=False, indent=2),
        )

        try:
            response_text = llm_chat(prompt, max_tokens=4096)

            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == 0:
                logger.warning("[Strategist] No JSON in response")
                return {"error": "no_json", "raw": response_text[:300]}

            return json.loads(response_text[start:end])

        except json.JSONDecodeError as e:
            logger.error(f"[Strategist] JSON parse error: {e}")
            return {"error": "parse_failed"}
        except Exception as e:
            logger.error(f"[Strategist] Error: {e}")
            return {"error": "api_error", "message": str(e)}

    def score_products(self, product_suggestions: list[dict]) -> list[dict]:
        """综合评分，找出最佳 ROI 产品

        综合分 = ROI 权重 0.4 + 自动化权重 0.35 + 传播权重 0.25
        """
        for p in product_suggestions:
            roi = float(p.get("roi_score", 0))
            auto = float(p.get("automation_score", 0))
            viral = float(p.get("viral_score", 0))
            p["composite_score"] = round(roi * 0.4 + auto * 0.35 + viral * 0.25, 2)

        return sorted(product_suggestions, key=lambda x: float(x.get("composite_score", 0)), reverse=True)

    async def generate_and_score(self, topic: str, emotion_analysis: dict) -> dict:
        """生成并排序产品建议（便利方法）"""
        report = await self.generate(topic, emotion_analysis)
        if "error" not in report:
            products = report.get("product_suggestions", [])
            report["product_suggestions"] = self.score_products(products)
            # 更新 best_product 为评分最高的
            if report["product_suggestions"]:
                report["best_product"] = report["product_suggestions"][0].get("type", "")
        return report
