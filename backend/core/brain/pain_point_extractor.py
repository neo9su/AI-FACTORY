"""Brain 痛点提取器"""


class PainPointExtractor:
    PAIN_CATEGORIES: dict[str, list[str]] = {
        "self_worth": ["自卑", "不够好", "被看不起"],
        "social": ["孤独", "社交恐惧", "没朋友"],
        "money": ["赋闲", "没钱", "副业"],
        "love": ["分手", "失恋", "不被爱"],
        "future": ["迷茫", "内耗", "无目标"],
    }

    def extract(self, emotion_result: dict) -> dict:
        return {
            "pain_points": emotion_result.get("pain_points", []),
            "willingness_to_pay": emotion_result.get("willingness_to_pay_trigger", ""),
            "primary_emotion": emotion_result.get("primary_emotion", ""),
            "identity_factor": emotion_result.get("identity_factor", ""),
            "product_hint": emotion_result.get("product_opportunity_hint", ""),
        }

    def categorize_pain(self, pain_points: list[str]) -> dict[str, list[str]]:
        categorized: dict[str, list[str]] = {cat: [] for cat in self.PAIN_CATEGORIES}
        categorized["other"] = []
        for pain in pain_points:
            matched = False
            for category, keywords in self.PAIN_CATEGORIES.items():
                if any(kw in pain for kw in keywords):
                    categorized[category].append(pain)
                    matched = True
                    break
            if not matched:
                categorized["other"].append(pain)
        return {k: v for k, v in categorized.items() if v}
