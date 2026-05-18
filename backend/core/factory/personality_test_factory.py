"""AI 人格测试 H5 生成工厂 — 生成可直接发布的心理测试题"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

PERSONALITY_TEST_PROMPT = """\
你是一位爆款心理测试设计师，精通用MBTI/依恋理论/九型人格等框架设计高传播测试。

商机主题: {topic}
核心情绪: {emotions}
目标受众: {audience}
身份认同因素: {identity_factor}
爆点公式: {viral_formula}

请生成一套完整的心理测试，必须返回纯 JSON（不要 markdown 代码块）:

{{
  "test_name": "测试名称（含情绪钩子，如\"你是哪种孤独星人?\"）",
  "tagline": "分享钩子语（用户完成后愿意分享的一句话，≤15字）",
  "description": "测试简介（3句话，让用户想点击）",
  "estimated_minutes": 3,
  "questions": [
    {{
      "id": 1,
      "text": "题目文字",
      "type": "single_choice",
      "options": [
        {{"id": "A", "text": "选项文字", "scores": {{"type_a": 3, "type_b": 1, "type_c": 0, "type_d": 0}}}},
        {{"id": "B", "text": "选项文字", "scores": {{"type_a": 0, "type_b": 3, "type_c": 1, "type_d": 0}}}},
        {{"id": "C", "text": "选项文字", "scores": {{"type_a": 0, "type_b": 1, "type_c": 3, "type_d": 0}}}},
        {{"id": "D", "text": "选项文字", "scores": {{"type_a": 1, "type_b": 0, "type_c": 0, "type_d": 3}}}}
      ]
    }}
  ],
  "result_types": [
    {{
      "id": "type_a",
      "name": "类型名称（简短有力）",
      "emoji": "🌙",
      "description": "200字描述（高度共鸣，让用户觉得被看见）",
      "strengths": ["优势1", "优势2", "优势3"],
      "growth_tips": ["成长建议1", "成长建议2"],
      "famous_example": "著名同类型人物",
      "share_text": "适合分享的一句话总结"
    }}
  ],
  "viral_hook": "结果页底部的传播钩子（让用户想@朋友来测）",
  "upsell_hint": "付费引导文案（引导购买相关电子书/咨询）"
}}

要求:
- 10道题，4个结果类型
- 题目要有画面感，让用户看了有共鸣
- 结果描述要有"被看见"的感觉，不要泛泛而谈
- viral_hook 要制造"我的朋友一定要测一下"的冲动
- 题目涵盖: 日常行为/情绪反应/人际关系/内心渴望
"""

H5_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{test_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
  .card {{ background: white; border-radius: 20px; padding: 30px; max-width: 480px; width: 100%; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }}
  .title {{ font-size: 24px; font-weight: 700; text-align: center; color: #2d3748; margin-bottom: 8px; }}
  .tagline {{ text-align: center; color: #718096; margin-bottom: 24px; font-size: 14px; }}
  .progress {{ height: 4px; background: #e2e8f0; border-radius: 2px; margin-bottom: 24px; }}
  .progress-bar {{ height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 2px; transition: width 0.3s; }}
  .question {{ font-size: 18px; font-weight: 600; color: #2d3748; margin-bottom: 20px; line-height: 1.5; }}
  .option {{ padding: 14px 18px; border: 2px solid #e2e8f0; border-radius: 12px; margin-bottom: 10px; cursor: pointer; transition: all 0.2s; color: #4a5568; }}
  .option:hover {{ border-color: #667eea; background: #f0f0ff; color: #667eea; }}
  .option.selected {{ border-color: #667eea; background: #667eea; color: white; }}
  .btn {{ width: 100%; padding: 14px; background: linear-gradient(90deg, #667eea, #764ba2); color: white; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 16px; }}
  .result {{ display: none; text-align: center; }}
  .result-emoji {{ font-size: 64px; margin-bottom: 16px; }}
  .result-name {{ font-size: 28px; font-weight: 700; color: #2d3748; margin-bottom: 12px; }}
  .result-desc {{ color: #4a5568; line-height: 1.7; margin-bottom: 20px; }}
  .share-btn {{ background: linear-gradient(90deg, #f6ad55, #ed8936); }}
</style>
</head>
<body>
<div class="card">
  <div id="quiz-section">
    <div class="title">{test_name}</div>
    <div class="tagline">{tagline}</div>
    <div class="progress"><div class="progress-bar" id="progress" style="width:10%"></div></div>
    <div class="question" id="question-text"></div>
    <div id="options"></div>
    <button class="btn" id="next-btn" onclick="nextQuestion()" style="display:none">继续 →</button>
  </div>
  <div class="result" id="result-section">
    <div class="result-emoji" id="r-emoji"></div>
    <div class="result-name" id="r-name"></div>
    <div class="result-desc" id="r-desc"></div>
    <div style="color:#718096;font-size:13px;margin-bottom:16px" id="r-hook"></div>
    <button class="btn" onclick="location.reload()">再测一次</button>
    <button class="btn share-btn" style="margin-top:10px" onclick="shareResult()">分享结果 🎉</button>
  </div>
</div>
<script>
const data = {quiz_data_json};
let current = 0;
let scores = {{}};
data.result_types.forEach(t => scores[t.id] = 0);

function loadQuestion() {{
  const q = data.questions[current];
  document.getElementById('question-text').textContent = (current+1) + '. ' + q.text;
  document.getElementById('progress').style.width = ((current+1)/data.questions.length*100) + '%';
  const opts = document.getElementById('options');
  opts.innerHTML = '';
  q.options.forEach(opt => {{
    const div = document.createElement('div');
    div.className = 'option';
    div.textContent = opt.id + '. ' + opt.text;
    div.onclick = () => selectOption(div, opt);
    opts.appendChild(div);
  }});
  document.getElementById('next-btn').style.display = 'none';
}}

function selectOption(el, opt) {{
  document.querySelectorAll('.option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
  Object.entries(opt.scores).forEach(([k,v]) => scores[k] = (scores[k]||0) + v);
  document.getElementById('next-btn').style.display = 'block';
}}

function nextQuestion() {{
  current++;
  if (current >= data.questions.length) showResult();
  else loadQuestion();
}}

function showResult() {{
  const winner = Object.entries(scores).sort((a,b)=>b[1]-a[1])[0][0];
  const res = data.result_types.find(t => t.id === winner);
  document.getElementById('quiz-section').style.display = 'none';
  document.getElementById('result-section').style.display = 'block';
  document.getElementById('r-emoji').textContent = res.emoji;
  document.getElementById('r-name').textContent = res.name;
  document.getElementById('r-desc').textContent = res.description;
  document.getElementById('r-hook').textContent = data.viral_hook;
}}

function shareResult() {{ alert(data.upsell_hint || '分享给好友一起测试！'); }}

loadQuestion();
</script>
</body></html>
"""


class PersonalityTestFactory:
    """AI 人格测试 H5 生成工厂"""

    MODEL = "claude-sonnet-4-5"

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic()

    async def generate_test_data(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """生成测试题目数据（JSON 结构）"""
        topic = opportunity.get("topic", "")
        emotions = ", ".join(opportunity.get("core_emotions", []))
        audience = opportunity.get("audience_profile", "年轻人")
        identity = opportunity.get("identity_factor", "")
        viral = opportunity.get("viral_formula", "")

        prompt = PERSONALITY_TEST_PROMPT.format(
            topic=topic,
            emotions=emotions,
            audience=audience,
            identity_factor=identity,
            viral_formula=viral,
        )

        logger.info(f"[PersonalityTestFactory] Generating test for: {topic[:40]}")
        message = await self._client.messages.create(
            model=self.MODEL,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(raw)

    async def generate_h5(
        self, opportunity: dict[str, Any]
    ) -> dict[str, Any]:
        """生成完整 H5 测试页面"""
        test_data = await self.generate_test_data(opportunity)
        quiz_json = json.dumps(test_data, ensure_ascii=False)
        html = H5_TEMPLATE.format(
            test_name=test_data.get("test_name", "心理测试"),
            tagline=test_data.get("tagline", "测测你是哪种类型"),
            quiz_data_json=quiz_json,
        )
        return {
            "product_type": "personality_test",
            "title": test_data.get("test_name", ""),
            "tagline": test_data.get("tagline", ""),
            "description": test_data.get("description", ""),
            "html_content": html,
            "test_data": test_data,
            "status": "ready",
        }
