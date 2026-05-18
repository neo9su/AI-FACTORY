"""NeuroTrend Brain — 核心分析 Prompts"""

EMOTION_ANALYSIS_PROMPT = """你是一位顶尖的消费心理学专家和行为经济学研究员。

分析以下互联网内容，深度解读人类情绪层次：

内容：{content}
来源：{source}
互动数据：{engagement}

请从以下维度分析，必须返回纯 JSON（不要加 markdown 代码块）：

1. primary_emotion: 主要情绪（anxiety | desire | vanity | loneliness | inferiority | achievement | escapism | money_desire | social_approval）
2. emotion_intensity: 0-10
3. underlying_desire: 潜意识欲望（1-2句）
4. pain_points: [3-5个痛点]
5. willingness_to_pay_trigger: 付费触发点
6. identity_factor: 身份认同因素
7. viral_formula: 爆点公式
8. product_opportunity_hint: 产品机会提示

返回纯 JSON：
{{
  "primary_emotion": "...",
  "emotion_intensity": 8,
  "underlying_desire": "...",
  "pain_points": ["..."],
  "willingness_to_pay_trigger": "...",
  "identity_factor": "...",
  "viral_formula": "...",
  "product_opportunity_hint": "..."
}}"""

OPPORTUNITY_GENERATION_PROMPT = """你是 AI 创业机会分析师。

热点主题：{topic}
情绪分析：{emotion_analysis}

返回纯 JSON：
{{
  "topic": "...",
  "why_viral": "...",
  "core_emotions": [],
  "core_pain_points": [],
  "willingness_to_pay": "...",
  "product_suggestions": [{{"type": "ebook", "title": "...", "description": "...", "target_user": "...", "price_range": "$5-15", "roi_score": 8.5, "automation_score": 9.0, "viral_score": 7.0, "time_to_build": "1天", "why_this_works": "..."}}],
  "best_product": "...",
  "best_product_reason": "...",
  "market_analysis": {{"market_size": "...", "competitors": [], "competitive_advantage": "...", "seo_value": "high", "lifecycle": "evergreen"}},
  "content_angles": [],
  "hook_lines": [],
  "action_plan": {{"day1": "...", "week1": "...", "month1": "..."}}
}}"""
