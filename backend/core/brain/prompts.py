"""NeuroTrend Brain — 核心分析 Prompts（消费心理学 × 行为经济学 × 人性洞察）"""

EMOTION_ANALYSIS_PROMPT = """\
你是一位顶尖的消费心理学专家和行为经济学研究员，专门研究数字时代的人类情绪驱动机制。

分析以下互联网内容，深度解读其情绪层次：

内容：{content}
来源：{source}
互动数据：{engagement}

请深入分析以下维度，返回纯 JSON（不要 markdown 代码块）：

1. primary_emotion - 主要情绪（anxiety|desire|vanity|loneliness|inferiority|achievement|escapism|money_desire|social_approval）
2. secondary_emotions - 次要情绪列表（1-2个，同上枚举）
3. emotion_intensity - 情绪强度 0-10
4. underlying_desire - 潜意识欲望（1-2句，直指人性，例："渴望被看见但又害怕被评判的矛盾心理"）
5. pain_points - 痛点列表（3-5个，用普通人的语言表达，不要学术词汇）
6. willingness_to_pay_trigger - 付费心理触发点（具体说明用户愿意为什么掏钱）
7. identity_factor - 身份认同因素（如 "INFJ人格" / "副业达人" / "高敏感人群"）
8. viral_formula - 爆点公式（情绪×身份×欲望×传播性，用一句话说明为什么会传播）
9. product_opportunity_hint - 产品机会直觉提示（2-3句，说明最适合的产品形态）
10. audience_profile - 目标受众画像（年龄/性别倾向/核心特征，简短描述）

返回纯 JSON：
{{
  "primary_emotion": "...",
  "secondary_emotions": ["..."],
  "emotion_intensity": 8,
  "underlying_desire": "...",
  "pain_points": ["...", "...", "..."],
  "willingness_to_pay_trigger": "...",
  "identity_factor": "...",
  "viral_formula": "...",
  "product_opportunity_hint": "...",
  "audience_profile": "..."
}}"""

OPPORTUNITY_GENERATION_PROMPT = """\
你是顶尖的 AI 创业机会分析师，擅长将人类情绪转化为可商业化的 AI 产品机会。
你特别擅长：人格/心理内容、情绪疗愈产品、AI陪伴类产品。

热点主题：{topic}
情绪分析数据：{emotion_analysis}

基于以上数据，生成完整的商业机会报告。返回纯 JSON：

{{
  "topic": "热点主题",
  "why_viral": "为什么这个话题会火（2-3句，结合情绪分析）",
  "core_emotions": ["情绪1", "情绪2"],
  "core_pain_points": ["痛点1", "痛点2", "痛点3"],
  "willingness_to_pay": "用户愿意为什么付费（具体说明，而不是泛泛而谈）",

  "product_suggestions": [
    {{
      "type": "ebook|personality_test|short_video|comic_drama|website|saas|ai_agent|audio|pdf_report",
      "title": "具体产品名称（吸引人，不要太学术）",
      "description": "一句话描述产品核心价值",
      "target_user": "目标用户画像",
      "price_range": "$X-Y 或 ¥X-Y",
      "roi_score": 8.5,
      "automation_score": 9.0,
      "viral_score": 7.5,
      "time_to_build": "1天|3天|1周|1月",
      "why_this_works": "为什么这个产品能卖（结合情绪分析）",
      "monetization_model": "变现模式（一次性购买/订阅/广告/带货）",
      "platform": "最适合发布的平台"
    }}
  ],

  "best_product": "最推荐的产品type",
  "best_product_reason": "为什么这个ROI最高（3-4句，要有说服力）",

  "market_analysis": {{
    "market_size": "潜在市场规模描述（要具体）",
    "competitors": ["竞争对手1", "竞争对手2"],
    "competitive_advantage": "我们的差异化优势",
    "seo_value": "high|medium|low",
    "lifecycle": "evergreen|trending|seasonal"
  }},

  "hook_lines": [
    "钩子文案1（能让人立刻点击的标题）",
    "钩子文案2（情绪共鸣型）",
    "钩子文案3（痛点直击型）",
    "钩子文案4（好奇心驱动型）"
  ],

  "content_angles": [
    "内容切入角度1（最适合短视频的角度）",
    "内容切入角度2（最适合图文的角度）",
    "内容切入角度3（最适合长文的角度）"
  ],

  "monetization_strategy": {{
    "quick_win": "最快能赚到钱的方式（1-3天内）",
    "mid_term": "中期变现策略（1-4周）",
    "long_term": "长期护城河（1-3月+）"
  }},

  "action_plan": {{
    "day1": "第一天具体做什么（操作级，不要废话）",
    "week1": "第一周目标和关键里程碑",
    "month1": "第一个月核心目标"
  }}
}}"""
