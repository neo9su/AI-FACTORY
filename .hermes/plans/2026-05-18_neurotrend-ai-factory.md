# NeuroTrend AI Factory — 完整实施规划

> **项目定位：** AI 商业机会操作系统 — 自动发现人类情绪与欲望，并自动生成对应 AI 产品。

---

## 目标

构建「需求发现 → 用户心理分析 → 产品生成 → 自动发布 → 数据回流优化」全闭环系统。

**核心循环：**

```
互联网情绪 → AI理解人性 → AI发现商机 → AI生成产品 → AI自动营销 → 数据反馈 → AI继续优化
```

**真正的护城河：** 不是分析热点，而是分析人性。情绪需求洞察引擎，是整套系统的灵魂。

---

## 当前技术基础

- 已有：`~/autonomous-ai-factory/` — FastAPI + Next.js 14 + PostgreSQL + Redis + ARQ
- 已有：核心模块 `orchestrator / planner / executor / tester / gatekeeper`
- 已有：GPU Server (10.190.0.206)，本地 AI 推理能力（CosyVoice2 / Qwen3 等）
- 目标：在现有"AI 软件工厂"基础上，新增"商机发现 + 内容工厂"双引擎

---

## 系统整体架构（6层）

```
┌──────────────────────────────────────────────────────────┐
│  Layer 1: Hunter (数据采集层)                             │
│  Reddit · X/Twitter · 小红书 · 抖音 · ProductHunt · HF   │
├──────────────────────────────────────────────────────────┤
│  Layer 2: Brain (数据理解层)                              │
│  情绪分析 · 痛点提取 · 爆点因子 · 欲望模型               │
├──────────────────────────────────────────────────────────┤
│  Layer 3: Strategist (商机生成层) ← 最核心价值            │
│  AI产品建议 · ROI评估 · 市场分析 · 自动化评分            │
├──────────────────────────────────────────────────────────┤
│  Layer 4: Factory (产品生成层)                            │
│  AI电子书 · AI人格测试 · AI短视频 · AI漫剧 · AI网站      │
├──────────────────────────────────────────────────────────┤
│  Layer 5: Publisher (自动发布层)                          │
│  网站发布 · 视频发布 · SEO · 广告测试                    │
├──────────────────────────────────────────────────────────┤
│  Layer 6: Feedback Loop (数据回流层)                      │
│  销售数据 · 传播数据 · 模型再训练                        │
└──────────────────────────────────────────────────────────┘
```

---

## 分阶段实施路线

### Phase 0：环境改造（Week 1）
> 把现有 AI 软件工厂改造为支持"商机发现"的基础设施

### Phase 1：Hunter + Brain MVP（Week 2-3）
> 核心 MVP：热点 → 情绪 → AI 产品建议

### Phase 2：Strategist + 商机报告（Week 4-5）
> 生成结构化商业机会报告，带 ROI 评分

### Phase 3：Content Factory（Week 6-8）
> 自动生成 AI 电子书 / 人格测试 / 心理内容产品

### Phase 4：Publisher + 闭环（Week 9-12）
> 自动发布 + 数据回流 + 再优化

---

## Phase 0：环境改造

### Task 0.1：新增 NeuroTrend 数据库模型

**目标：** 在现有 PostgreSQL 中新增商机相关表

**Files:**
- Create: `backend/models/trend.py`
- Modify: `backend/models/__init__.py`
- Create: `backend/db/migrations/versions/xxx_add_trend_tables.py`

**新增数据表：**

```python
# backend/models/trend.py
"""NeuroTrend AI — 趋势、情绪、商机数据模型"""
import enum
from typing import Optional
from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.models.base import Base, TimestampMixin, UUIDMixin


class TrendSource(str, enum.Enum):
    REDDIT = "reddit"
    TWITTER = "twitter"
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    PRODUCT_HUNT = "product_hunt"
    HUGGING_FACE = "hugging_face"
    GITHUB = "github"
    GOOGLE_TRENDS = "google_trends"


class EmotionType(str, enum.Enum):
    ANXIETY = "anxiety"          # 焦虑
    DESIRE = "desire"            # 欲望
    VANITY = "vanity"            # 虚荣
    LONELINESS = "loneliness"    # 孤独
    INFERIORITY = "inferiority"  # 自卑
    ACHIEVEMENT = "achievement"  # 成就感
    ESCAPISM = "escapism"        # 逃避现实
    MONEY_DESIRE = "money_desire"  # 赚钱欲望
    SOCIAL_APPROVAL = "social_approval"  # 社交认同


class ProductType(str, enum.Enum):
    EBOOK = "ebook"
    PERSONALITY_TEST = "personality_test"
    SHORT_VIDEO = "short_video"
    COMIC_DRAMA = "comic_drama"
    WEBSITE = "website"
    SAAS = "saas"
    AI_AGENT = "ai_agent"
    AUDIO = "audio"
    PDF_REPORT = "pdf_report"


class TrendSignal(Base, UUIDMixin, TimestampMixin):
    """热点信号 — 从各平台抓取的原始数据"""
    __tablename__ = "trend_signals"

    source: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(2000))
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    # 分析结果（由Brain层填充）
    emotion_tags: Mapped[Optional[list]] = mapped_column(JSON)  # List[EmotionType]
    pain_points: Mapped[Optional[list]] = mapped_column(JSON)   # List[str]
    desire_factors: Mapped[Optional[list]] = mapped_column(JSON)
    viral_score: Mapped[float] = mapped_column(Float, default=0.0)
    analyzed: Mapped[bool] = mapped_column(default=False)


class OpportunityReport(Base, UUIDMixin, TimestampMixin):
    """商机报告 — Strategist层输出"""
    __tablename__ = "opportunity_reports"

    trend_signal_id: Mapped[str] = mapped_column(String(36))
    topic: Mapped[str] = mapped_column(Text)                    # 主题
    why_viral: Mapped[str] = mapped_column(Text)                # 为什么火
    core_emotions: Mapped[list] = mapped_column(JSON)           # 核心情绪
    core_pain_points: Mapped[list] = mapped_column(JSON)        # 核心痛点
    willingness_to_pay: Mapped[str] = mapped_column(Text)       # 愿意付费的点
    product_suggestions: Mapped[list] = mapped_column(JSON)     # 产品建议列表
    best_product: Mapped[Optional[str]] = mapped_column(String(100))  # 最佳产品类型
    roi_score: Mapped[float] = mapped_column(Float, default=0.0)      # ROI评分 0-10
    automation_score: Mapped[float] = mapped_column(Float, default=0.0)  # 自动化程度
    market_size: Mapped[Optional[str]] = mapped_column(Text)
    competitors: Mapped[Optional[list]] = mapped_column(JSON)
    seo_value: Mapped[Optional[str]] = mapped_column(String(20))  # high/medium/low
    lifecycle: Mapped[Optional[str]] = mapped_column(String(20))  # 生命周期
    full_report: Mapped[Optional[dict]] = mapped_column(JSON)


class ContentProduct(Base, UUIDMixin, TimestampMixin):
    """内容产品 — Factory层产出物"""
    __tablename__ = "content_products"

    opportunity_id: Mapped[str] = mapped_column(String(36))
    product_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[Optional[dict]] = mapped_column(JSON)       # 产品内容
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="draft")
    publish_urls: Mapped[Optional[list]] = mapped_column(JSON)  # 发布地址
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
```

**步骤：**
```bash
cd ~/autonomous-ai-factory
# 1. 创建模型文件（见上）
# 2. 运行 alembic 生成迁移
cd backend && alembic revision --autogenerate -m "add_trend_tables"
alembic upgrade head
```

---

### Task 0.2：新增 NeuroTrend API 路由骨架

**Files:**
- Create: `backend/api/trends.py`
- Create: `backend/api/opportunities.py`
- Modify: `backend/main.py`

```python
# backend/api/trends.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import get_session

router = APIRouter()

@router.post("/trends/scan")
async def trigger_trend_scan(
    sources: list[str] = ["reddit", "product_hunt"],
    session: AsyncSession = Depends(get_session)
):
    """触发热点扫描任务"""
    ...

@router.get("/trends")
async def list_trends(limit: int = 20, session: AsyncSession = Depends(get_session)):
    """获取最新热点信号"""
    ...

@router.post("/trends/{trend_id}/analyze")
async def analyze_trend(trend_id: str, session: AsyncSession = Depends(get_session)):
    """触发情绪+痛点分析"""
    ...
```

```python
# backend/api/opportunities.py
@router.get("/opportunities")
async def list_opportunities(min_roi: float = 6.0): ...

@router.get("/opportunities/{id}")
async def get_opportunity(id: str): ...

@router.post("/opportunities/{id}/generate-product")
async def generate_product(id: str, product_type: str): ...
```

---

## Phase 1：Hunter + Brain MVP

> **目标：** 证明系统能稳定发现商业机会。

### Task 1.1：实现 Reddit 热点爬虫

**Files:**
- Create: `backend/core/hunter/reddit_hunter.py`
- Create: `backend/core/hunter/__init__.py`
- Create: `backend/core/hunter/base.py`

**依赖安装：**
```bash
pip install praw httpx playwright
# 安装 playwright browsers
playwright install chromium
```

```python
# backend/core/hunter/base.py
"""Hunter 基类 — 所有爬虫继承此类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class RawSignal:
    source: str
    title: str
    content: str
    url: str
    engagement_score: float
    raw_data: dict[str, Any]


class BaseHunter(ABC):
    @abstractmethod
    async def hunt(self, keywords: list[str] | None = None, limit: int = 20) -> list[RawSignal]:
        """抓取信号，返回标准化数据"""
        ...

    async def save_to_db(self, signals: list[RawSignal], session) -> list[str]:
        """保存到数据库，返回 signal_ids"""
        ...
```

```python
# backend/core/hunter/reddit_hunter.py
"""Reddit 热点爬虫 — 抓取高情绪密度内容"""
import asyncio
import httpx
from backend.core.hunter.base import BaseHunter, RawSignal

# 高价值 subreddits（按情绪类型分类）
HIGH_EMOTION_SUBREDDITS = {
    "loneliness": ["lonely", "depression", "socialskills", "introvert"],
    "anxiety": ["anxiety", "careerguidance", "GetMotivated"],
    "money_desire": ["sidehustle", "passive_income", "financialindependence"],
    "identity": ["mbti", "infj", "personalitytypes"],
    "escapism": ["books", "manga", "webtoons", "webnovels"],
    "ai_trends": ["artificial", "MachineLearning", "ChatGPT"],
}

class RedditHunter(BaseHunter):
    BASE_URL = "https://www.reddit.com"

    async def hunt(self, subreddits: list[str] | None = None, limit: int = 20) -> list[RawSignal]:
        signals = []
        targets = subreddits or [s for group in HIGH_EMOTION_SUBREDDITS.values() for s in group]

        async with httpx.AsyncClient(headers={"User-Agent": "NeuroTrendBot/1.0"}) as client:
            for sub in targets[:5]:  # MVP 先限制5个
                try:
                    resp = await client.get(f"{self.BASE_URL}/r/{sub}/hot.json?limit={limit}")
                    data = resp.json()
                    for post in data["data"]["children"]:
                        p = post["data"]
                        signals.append(RawSignal(
                            source="reddit",
                            title=p["title"],
                            content=p.get("selftext", "")[:1000],
                            url=f"https://reddit.com{p['permalink']}",
                            engagement_score=p["score"] + p["num_comments"] * 3,
                            raw_data={
                                "subreddit": sub,
                                "upvote_ratio": p["upvote_ratio"],
                                "num_comments": p["num_comments"],
                                "awards": p.get("total_awards_received", 0),
                            }
                        ))
                    await asyncio.sleep(1)  # 避免限速
                except Exception as e:
                    print(f"Reddit {sub} error: {e}")

        # 按情绪密度排序（评分+评论*3）
        return sorted(signals, key=lambda x: x.engagement_score, reverse=True)
```

---

### Task 1.2：Product Hunt 爬虫

**Files:**
- Create: `backend/core/hunter/producthunt_hunter.py`

```python
# backend/core/hunter/producthunt_hunter.py
"""Product Hunt 趋势爬虫 — 捕获 AI 产品方向"""
import httpx
from backend.core.hunter.base import BaseHunter, RawSignal

PRODUCTHUNT_GQL = "https://api.producthunt.com/v2/api/graphql"

TRENDING_QUERY = """
query {
  posts(first: 20, order: VOTES, topic: "artificial-intelligence") {
    edges {
      node {
        id name tagline description
        votesCount commentsCount
        url
        topics { edges { node { name } } }
      }
    }
  }
}
"""

class ProductHuntHunter(BaseHunter):
    def __init__(self, api_token: str):
        self.api_token = api_token

    async def hunt(self, keywords=None, limit=20) -> list[RawSignal]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                PRODUCTHUNT_GQL,
                json={"query": TRENDING_QUERY},
                headers={"Authorization": f"Bearer {self.api_token}",
                         "Content-Type": "application/json"}
            )
            data = resp.json()
            signals = []
            for edge in data["data"]["posts"]["edges"]:
                n = edge["node"]
                signals.append(RawSignal(
                    source="product_hunt",
                    title=n["name"],
                    content=f"{n['tagline']}\n{n['description'] or ''}",
                    url=n["url"],
                    engagement_score=n["votesCount"] + n["commentsCount"] * 2,
                    raw_data={
                        "votes": n["votesCount"],
                        "comments": n["commentsCount"],
                        "topics": [e["node"]["name"] for e in n["topics"]["edges"]],
                    }
                ))
        return sorted(signals, key=lambda x: x.engagement_score, reverse=True)
```

---

### Task 1.3：Brain — 情绪分析引擎（核心）

> 这是系统最核心的模块。用 LLM 做深层情绪+痛点推理。

**Files:**
- Create: `backend/core/brain/__init__.py`
- Create: `backend/core/brain/emotion_analyzer.py`
- Create: `backend/core/brain/pain_point_extractor.py`
- Create: `backend/core/brain/viral_factor_analyzer.py`
- Create: `backend/core/brain/prompts.py`

```python
# backend/core/brain/prompts.py
"""NeuroTrend Brain — 核心分析 Prompts"""

EMOTION_ANALYSIS_PROMPT = """
你是一位顶尖的消费心理学专家和行为经济学研究员。

分析以下互联网内容，深度解读人类情绪层次：

内容：{content}
来源：{source}
互动数据：{engagement}

请从以下维度分析（用JSON返回）：

1. primary_emotion: 主要情绪（从以下选择）
   - anxiety（焦虑）
   - desire（欲望）
   - vanity（虚荣）
   - loneliness（孤独）
   - inferiority（自卑）
   - achievement（成就感）
   - escapism（逃避现实）
   - money_desire（赚钱欲望）
   - social_approval（社交认同）

2. emotion_intensity: 情绪强度 0-10

3. underlying_desire: 潜意识欲望（1-2句话，直指人性）
   例："渴望被看见但又害怕被评判的矛盾心理"

4. pain_points: 痛点列表（3-5个，用人话表达）

5. willingness_to_pay_trigger: 愿意付费的心理触发点

6. identity_factor: 身份认同因素（如"INFJ人格" / "副业达人"）

7. viral_formula: 爆点公式
   情绪×身份×欲望×传播性 → 简短说明

8. product_opportunity_hint: 对应产品机会的直觉提示

返回格式：
{
  "primary_emotion": "...",
  "emotion_intensity": 8,
  "underlying_desire": "...",
  "pain_points": ["...", "..."],
  "willingness_to_pay_trigger": "...",
  "identity_factor": "...",
  "viral_formula": "...",
  "product_opportunity_hint": "..."
}
"""

OPPORTUNITY_GENERATION_PROMPT = """
你是一位 AI 创业机会分析师，擅长将人类情绪转化为可商业化的 AI 产品机会。

基于以下情绪分析数据，生成结构化商业机会报告：

热点主题：{topic}
核心情绪：{emotion_analysis}

请输出完整的商业机会报告（JSON格式）：

{
  "topic": "热点主题",
  "why_viral": "为什么这个话题会火（2-3句话）",
  "core_emotions": ["情绪1", "情绪2"],
  "core_pain_points": ["痛点1", "痛点2", "痛点3"],
  "willingness_to_pay": "用户愿意为什么付费（具体说明）",
  
  "product_suggestions": [
    {
      "type": "ebook",
      "title": "产品名称",
      "description": "一句话描述",
      "target_user": "目标用户",
      "price_range": "定价区间（美元）",
      "roi_score": 8.5,           // 0-10，商业回报潜力
      "automation_score": 9.0,    // 0-10，可自动化程度
      "viral_score": 7.0,         // 0-10，传播潜力
      "time_to_build": "1天",
      "why_this_works": "为什么这个产品能卖"
    }
  ],
  
  "best_product": "最推荐的产品类型",
  "best_product_reason": "为什么这个ROI最高",
  
  "market_analysis": {
    "market_size": "潜在市场规模描述",
    "competitors": ["竞争对手1", "竞争对手2"],
    "competitive_advantage": "我们的差异化优势",
    "seo_value": "high/medium/low",
    "lifecycle": "evergreen/trending/seasonal"
  },
  
  "content_angles": ["内容切入角度1", "内容切入角度2"],
  "hook_lines": ["钩子文案1", "钩子文案2", "钩子文案3"],
  
  "action_plan": {
    "day1": "第一天做什么",
    "week1": "第一周目标",
    "month1": "第一个月目标"
  }
}
"""
```

```python
# backend/core/brain/emotion_analyzer.py
"""情绪分析引擎 — 深度解读人类情绪"""
import json
import anthropic
from backend.core.brain.prompts import EMOTION_ANALYSIS_PROMPT
from backend.core.hunter.base import RawSignal


class EmotionAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic()

    async def analyze(self, signal: RawSignal) -> dict:
        """分析单个信号的情绪层次"""
        content = f"标题：{signal.title}\n内容：{signal.content}"

        prompt = EMOTION_ANALYSIS_PROMPT.format(
            content=content,
            source=signal.source,
            engagement=f"互动分数: {signal.engagement_score}"
        )

        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text
        # 提取 JSON
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            return json.loads(response_text[start:end])
        except Exception:
            return {"error": "parse_failed", "raw": response_text}

    async def batch_analyze(self, signals: list[RawSignal]) -> list[dict]:
        """批量分析（带进度日志）"""
        results = []
        for i, signal in enumerate(signals):
            print(f"[Brain] 分析 {i+1}/{len(signals)}: {signal.title[:50]}...")
            result = await self.analyze(signal)
            results.append(result)
        return results
```

---

### Task 1.4：Strategist — 商机生成器

**Files:**
- Create: `backend/core/strategist/__init__.py`
- Create: `backend/core/strategist/opportunity_generator.py`

```python
# backend/core/strategist/opportunity_generator.py
"""商机生成器 — 将情绪数据转化为商业机会"""
import json
import anthropic
from backend.core.brain.prompts import OPPORTUNITY_GENERATION_PROMPT


class OpportunityGenerator:
    def __init__(self):
        self.client = anthropic.Anthropic()

    async def generate(self, topic: str, emotion_analysis: dict) -> dict:
        """生成完整商业机会报告"""
        prompt = OPPORTUNITY_GENERATION_PROMPT.format(
            topic=topic,
            emotion_analysis=json.dumps(emotion_analysis, ensure_ascii=False, indent=2)
        )

        message = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            return json.loads(response_text[start:end])
        except Exception:
            return {"error": "parse_failed", "raw": response_text[:500]}

    def score_products(self, product_suggestions: list[dict]) -> list[dict]:
        """综合评分，找出最佳 ROI 产品"""
        for p in product_suggestions:
            # 综合分 = ROI权重0.4 + 自动化权重0.35 + 传播权重0.25
            roi = p.get("roi_score", 0)
            auto = p.get("automation_score", 0)
            viral = p.get("viral_score", 0)
            p["composite_score"] = round(roi * 0.4 + auto * 0.35 + viral * 0.25, 2)

        return sorted(product_suggestions, key=lambda x: x.get("composite_score", 0), reverse=True)
```

---

### Task 1.5：ARQ Worker — 异步任务队列集成

**Files:**
- Create: `backend/workers/trend_worker.py`
- Modify: `backend/workers/__init__.py`

```python
# backend/workers/trend_worker.py
"""NeuroTrend 异步工作队列"""
from backend.core.hunter.reddit_hunter import RedditHunter
from backend.core.brain.emotion_analyzer import EmotionAnalyzer
from backend.core.strategist.opportunity_generator import OpportunityGenerator
from backend.db.session import AsyncSessionLocal
from backend.models.trend import TrendSignal, OpportunityReport


async def run_trend_scan(ctx, sources: list[str] = ["reddit"]):
    """完整的 Hunter → Brain → Strategist 流水线"""
    async with AsyncSessionLocal() as session:
        all_signals = []

        # 1. Hunter：抓取数据
        if "reddit" in sources:
            hunter = RedditHunter()
            signals = await hunter.hunt(limit=10)
            all_signals.extend(signals)

        # 2. 保存原始信号到 DB
        for s in all_signals:
            db_signal = TrendSignal(
                source=s.source, title=s.title, content=s.content,
                url=s.url, engagement_score=s.engagement_score, raw_data=s.raw_data
            )
            session.add(db_signal)
        await session.commit()

        # 3. Brain：情绪分析
        analyzer = EmotionAnalyzer()
        top_signals = sorted(all_signals, key=lambda x: x.engagement_score, reverse=True)[:5]

        for signal in top_signals:
            emotion_data = await analyzer.analyze(signal)

            # 4. Strategist：生成商机
            generator = OpportunityGenerator()
            opportunity = await generator.generate(signal.title, emotion_data)
            scored_products = generator.score_products(
                opportunity.get("product_suggestions", [])
            )
            opportunity["product_suggestions"] = scored_products

            # 5. 保存商机报告
            report = OpportunityReport(
                topic=signal.title,
                why_viral=opportunity.get("why_viral", ""),
                core_emotions=opportunity.get("core_emotions", []),
                core_pain_points=opportunity.get("core_pain_points", []),
                willingness_to_pay=opportunity.get("willingness_to_pay", ""),
                product_suggestions=opportunity.get("product_suggestions", []),
                best_product=opportunity.get("best_product", ""),
                roi_score=scored_products[0].get("roi_score", 0) if scored_products else 0,
                automation_score=scored_products[0].get("automation_score", 0) if scored_products else 0,
                full_report=opportunity
            )
            session.add(report)

        await session.commit()
        return {"scanned": len(all_signals), "opportunities_generated": len(top_signals)}
```

---

### Task 1.6：前端 Dashboard — 商机看板

**Files:**
- Create: `frontend/app/opportunities/page.tsx`
- Create: `frontend/app/opportunities/[id]/page.tsx`
- Create: `frontend/components/opportunity-card.tsx`
- Create: `frontend/components/emotion-radar.tsx`

**核心页面功能：**

```
商机看板 (Opportunity Dashboard)
├── 顶部：触发扫描按钮 + 数据源选择
├── 商机卡片列表
│   ├── 热点主题
│   ├── 核心情绪标签（颜色编码）
│   ├── ROI评分 + 自动化评分（进度条）
│   ├── 最佳产品建议
│   └── 快速生成按钮
└── 详情页
    ├── 情绪分析雷达图
    ├── 痛点列表
    ├── 产品建议卡片（排序by ROI）
    ├── 完整商业分析报告
    └── 一键生成产品按钮
```

**情绪颜色系统：**
```tsx
const EMOTION_COLORS = {
  anxiety: "bg-orange-500",
  desire: "bg-pink-500",
  vanity: "bg-purple-500",
  loneliness: "bg-blue-400",
  money_desire: "bg-green-500",
  social_approval: "bg-yellow-500",
  escapism: "bg-indigo-500",
  achievement: "bg-emerald-500",
  inferiority: "bg-gray-500",
}
```

---

## Phase 2：商机报告 + 优先赛道深化

### Task 2.1：优先赛道爬虫（5星推荐方向）

针对最高ROI方向增加专项爬虫：

| 爬虫 | 目标 | 优先级 |
|------|------|--------|
| `mbti_hunter.py` | Reddit/X 上的 MBTI / 人格讨论 | ⭐⭐⭐⭐⭐ |
| `healing_hunter.py` | 情绪疗愈 / 焦虑 / 孤独内容 | ⭐⭐⭐⭐⭐ |
| `love_hunter.py` | 恋爱 / 分手 / AI陪伴相关 | ⭐⭐⭐⭐⭐ |
| `sidehustle_hunter.py` | 副业 / 赚钱 / 被动收入 | ⭐⭐⭐⭐ |
| `hf_hunter.py` | HuggingFace 热门模型 | ⭐⭐⭐⭐ |

### Task 2.2：增强版商机报告

新增字段：
- `hook_lines`: 3条可直接用的营销文案钩子
- `content_angles`: 内容创作切入角度
- `action_plan`: 1天/1周/1月行动计划
- `monetization_strategy`: 具体变现策略

---

## Phase 3：Content Factory — AI 内容产品工厂

### Task 3.1：AI 电子书生成器（最高自动化优先）

**Files:**
- Create: `backend/core/factory/__init__.py`
- Create: `backend/core/factory/ebook_generator.py`
- 依赖: `pip install reportlab weasyprint markdown2`

```python
# backend/core/factory/ebook_generator.py
"""AI 电子书/心理PDF 生成器"""

EBOOK_TYPES = {
    "personality_analysis": {
        "title_template": "{personality_type}人格深度解析：你的隐藏优势与成长密码",
        "chapters": [
            "你是谁：{type}人格的核心特质",
            "你的潜意识欲望：隐藏在行为背后的真相",
            "你在恋爱中的模式：吸引与排斥的心理机制",
            "你的职业天花板：突破瓶颈的3个核心策略",
            "你与世界的关系：如何让别人真正理解你",
        ]
    },
    "anxiety_guide": {
        "title_template": "高敏感人群生存指南：把焦虑变成超能力",
        "chapters": [...]
    },
    "healing_journal": {
        "title_template": "30天情绪疗愈日记：从内耗到内力的蜕变",
        "chapters": [...]
    }
}

class EbookGenerator:
    async def generate_outline(self, opportunity: dict, ebook_type: str) -> dict: ...
    async def generate_chapter(self, outline: dict, chapter_index: int) -> str: ...
    async def compile_pdf(self, chapters: list[str], metadata: dict) -> str: ...
```

### Task 3.2：AI 人格测试生成器

**产品形态：** 在线心理测验网站（可用 Next.js 快速生成）

```python
# backend/core/factory/quiz_generator.py
"""AI 人格测试题目生成器"""

QUIZ_TYPES = [
    "dark_side_personality",   # "你的隐藏黑暗面人格测试"
    "love_attachment_style",   # "你的恋爱依恋类型"
    "anxiety_type",            # "你属于哪种焦虑类型"
    "money_mindset",           # "你的金钱心理类型"
    "social_battery",          # "你的社交电量测试"
]

class QuizGenerator:
    async def generate_quiz(self, topic: str, num_questions: int = 10) -> dict:
        """生成完整测验题目+选项+计分逻辑+结果解读"""
        ...
    
    async def generate_result_pages(self, quiz: dict) -> list[dict]:
        """生成各类型结果页（含深度解读）"""
        ...
    
    async def compile_web_app(self, quiz: dict) -> str:
        """生成完整的 Next.js 测验网站代码"""
        ...
```

### Task 3.3：AI 短视频脚本生成器

**文件:** `backend/core/factory/video_script_generator.py`

```
输入：商机报告 + 情绪分析
输出：
  - 短视频脚本（15s/30s/60s 三个版本）
  - 分镜头描述
  - 配音文本（可直接接 CosyVoice2）
  - 背景音乐建议
  - 字幕文案
  - 发布策略（最佳时间/标题/标签）
```

### Task 3.4：ComfyUI 集成 — AI 漫剧生成

**Files:**
- Create: `backend/core/factory/comic_generator.py`
- 对接 GPU Server (10.190.0.206) 上的 ComfyUI

```python
# backend/core/factory/comic_generator.py
"""AI 情绪漫剧生成器 — 对接 ComfyUI"""

COMIC_STYLES = {
    "webtoon_healing": "治愈风格漫画，柔和色彩，温暖笔触",
    "dark_psychological": "心理暗黑风格，高对比度",
    "romance_modern": "现代都市恋爱风格",
}

class ComicGenerator:
    def __init__(self, comfyui_url: str = "http://10.190.0.206:8188"):
        self.comfyui_url = comfyui_url
    
    async def generate_panel(self, script: str, style: str) -> bytes: ...
    async def generate_episode(self, panels: list[str], style: str) -> list[bytes]: ...
```

---

## Phase 4：Publisher + 闭环

### Task 4.1：自动建站发布器

```python
# backend/core/publisher/site_publisher.py
"""自动建站 + 发布器"""
# 方案：使用 Vercel API 一键部署 Next.js 测验网站
```

### Task 4.2：SEO 自动化

- 自动生成 meta tags
- 自动生成 sitemap
- 关键词密度优化
- Schema.org 结构化数据

### Task 4.3：数据回流

```python
# backend/core/feedback/revenue_tracker.py
"""销售 + 传播数据回流"""
# 收集：浏览量、转化率、收入、用户留存
# 反馈：更新 OpportunityReport 的实际表现
# 优化：调整 Strategist 的产品推荐权重
```

---

## 重点赛道产品矩阵

### 🎯 最优先：人格/心理类产品

| 产品 | 平台 | 变现模式 | 预估ROI |
|------|------|----------|---------|
| MBTI深度分析PDF | 小红书/个人网站 | 直接购买 $5-15 | ⭐⭐⭐⭐⭐ |
| 恋爱依恋类型测试 | H5网站 | 广告+增值 | ⭐⭐⭐⭐⭐ |
| 高敏感人群生存指南 | 亚马逊KDP | 出版收入 | ⭐⭐⭐⭐ |
| AI心理咨询师Bot | Telegram/微信 | 订阅 $9.9/月 | ⭐⭐⭐⭐⭐ |

### 🎯 次优先：情绪内容类产品

| 产品 | 平台 | 变现模式 | 预估ROI |
|------|------|----------|---------|
| 治愈系AI情绪短视频 | 抖音/TikTok | 带货+广告 | ⭐⭐⭐⭐⭐ |
| AI情绪漫剧 | 小红书/B站 | 打赏+订阅 | ⭐⭐⭐⭐ |
| 情绪疗愈有声书 | 喜马拉雅 | 付费专辑 | ⭐⭐⭐⭐ |

---

## 技术栈总览

| 层 | 技术 | 说明 |
|----|------|------|
| 数据采集 | Python + httpx + Playwright | 无头浏览器处理动态页面 |
| 消息队列 | ARQ (Redis) | 现有基础设施 |
| 向量存储 | pgvector (PostgreSQL扩展) | 语义搜索历史信号 |
| 情绪分析 | Claude claude-opus-4-5 | 深度心理推理 |
| 电子书生成 | Claude + ReportLab | PDF生成 |
| 视频脚本 | Claude + CosyVoice2 | 本地TTS配音 |
| AI漫剧 | ComfyUI + SDXL/Flux | GPU Server |
| 前端 | Next.js 14 (现有) | 商机看板 + 内容管理 |
| 部署 | Vercel API | 自动发布测验网站 |

---

## 数据流示意

```
定时任务 (每6小时)
    ↓
Hunter 并发抓取
(Reddit · ProductHunt · HF ...)
    ↓
原始信号存储 (trend_signals 表)
    ↓
Brain 情绪分析 (Claude)
    ↓
Strategist 商机生成 (Claude)
    ↓
商机报告存储 (opportunity_reports 表)
    ↓
Dashboard 展示 (人工确认/AI自动选择)
    ↓
Factory 产品生成
(电子书 / 测验 / 视频脚本 / 漫剧)
    ↓
Publisher 自动发布
(网站 / 视频 / SEO)
    ↓
Feedback 数据回流
(销售额 / 传播量 / 转化率)
    ↓
优化 Strategist 权重
(哪类产品ROI最高 → 加大生成权重)
```

---

## 实施优先级（第一周聚焦）

```
Day 1-2: Task 0.1 + 0.2 (数据库模型 + API骨架)
Day 3:   Task 1.1 (Reddit Hunter 跑通)
Day 4:   Task 1.3 (Brain 情绪分析接通 Claude)
Day 5:   Task 1.4 (Strategist 商机报告生成)
Day 6:   Task 1.5 (ARQ Worker 串联流水线)
Day 7:   Task 1.6 (Dashboard 基础UI)
```

**MVP 验收标准：**
- 触发一次扫描，自动生成 ≥5 条商机报告
- 每条报告含：热点主题、核心情绪、产品建议（ROI排序）
- Dashboard 可视化展示，支持手动触发

---

## 风险与注意事项

1. **API 限速** — Reddit / ProductHunt 有请求频率限制，需实现重试+延迟
2. **内容合规** — 抓取内容仅用于分析，不直接转载
3. **LLM 成本** — 批量分析可用 claude-haiku 降低成本，重要分析用 claude-opus-4-5
4. **自动化边界** — Factory 生成的产品需人工审核后再发布（Phase 1-2）
5. **数据库向量化** — 建议后期加 pgvector，避免重复分析相似热点

---

*计划创建时间：2026-05-18*
*项目代号：NeuroTrend AI Factory*
*版本：v1.0 — Phase 0-1 详细实施规划*
