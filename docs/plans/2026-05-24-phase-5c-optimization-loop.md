# Phase 5-C: 持续优化闭环 (Continuous Optimization Loop)

> **核心:** 让系统从自己的发布数据中学习，自动优化内容策略、生成参数和发布时机，形成「自增长 AI 商业系统」的终极闭环。

**目标:** 基于 Phase 5-A (Analytics) 的反馈数据，自动调整 Phase 2~4 的内容生成策略，实现 A/B 测试 → 择优 → 迭代的持续优化循环。

**架构:**
```
Publish (5-B) → Analytics (5-A) → Performance Analyzer (5-C)
                                       ↓
                              Optimization Engine
                              ├── A/B Test Runner
                              ├── Hook/Title Optimizer
                              └── Content Angle Scorer
                                       ↓
                              Feedback Writer
                              ├── Update Brain Prompts
                              ├── Update Strategist Weights
                              └── Schedule Re-generation
                                       ↓
                              → Factory (Phase 4) → Publish (5-B) →
```

**新增文件:**
```
backend/
├── models/
│   └── optimization.py     ← 新增: 优化模式 / AB测试 / 内容表现
├── core/
│   └── optimizer/
│       ├── __init__.py
│       ├── performance_analyzer.py  ← 表现分析引擎
│       ├── ab_test_runner.py        ← A/B 测试框架
│       └── feedback_writer.py       ← 反馈写入器（更新 Brain/Strategist）
├── workers/
│   └── optimizer_worker.py  ← 新增: 优化 Worker
└── api/
    └── optimizer.py         ← 新增: 优化 API

frontend/
├── components/
│   └── ab-test-panel.tsx    ← A/B 测试结果对比面板
└── app/
    └── opportunities/
        └── [id]/
            └── optimize/
                └── page.tsx  ← 优化看板页
```

---

## Architecture — 3-Layer Design

### Layer 1: Performance Analyzer
负责从原始 engagement 数据中提取内容级别的表现模式。

**输入:** `product_engagements` + `opportunity_scores`
**输出:** `ContentPerformance` 结构化表现报告

```python
# 分析维度
class PerformanceSignal:
    hook_effectiveness: float      # 钩子→完播率
    angle_engagement: float        # 内容角度→互动率  
    format_preference: float       # 格式偏好（视频/测试/PDF）
    timing_sensitivity: float      # 发布时间敏感度
    audience_match_score: float    # 受众匹配度
```

### Layer 2: A/B Test Runner
自动生成多个内容变体，对比表现，择优迭代。

**流程:**
```
生成原文案 → LLM生成3个变体 → 发布到同一平台 → 追踪7天数据 → 选优 → 存档模式
```

**存储:**
```python
class ABTest(Base):
    product_id: str
    variants: list[dict]           # [{id, title, hook, content_diff}]
    engagement_by_variant: dict    # {variant_id: {views, plays, downloads}}
    winner_id: str | None
    tested_at: datetime
```

### Layer 3: Feedback Writer
将学习到的模式写回 Brain / Strategist / Factory 的配置和 prompts 中。

**三个反馈目标:**
1. **→ Brain Prompts**: 更新情绪分析权重、痛点关键词库
2. **→ Strategist**: 调整 `score_products()` 权重、机会生命周期预测
3. **→ Factory**: 更新内容模板、hook 模式库、标题生成规则

---

## Implementation Plan

### Task 1: Create Optimization Models

**Objective:** Define DB models for content performance patterns and A/B test results

**Files:**
- Create: `backend/models/optimization.py`

```python
"""Phase 5-C — 持续优化闭环数据模型."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.models.base import Base, UUIDMixin, TimestampMixin


class ContentPerformance(Base, UUIDMixin, TimestampMixin):
    """每个产品的表现分析快照 — 被 optimizer_worker 周期性写入。"""
    __tablename__ = "content_performances"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("content_products.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_reports.id", ondelete="SET NULL"), index=True
    )

    # ── 原始聚合数据 ──
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_plays: Mapped[int] = mapped_column(Integer, default=0)
    total_downloads: Mapped[int] = mapped_column(Integer, default=0)
    total_test_completes: Mapped[int] = mapped_column(Integer, default=0)

    # ── 行为指标（0~10 标准化） ──
    hook_retention_rate: Mapped[float] = mapped_column(Float, default=0.0)
    angle_click_rate: Mapped[float] = mapped_column(Float, default=0.0)
    format_completion_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # ── 衍生指标 ──
    engagement_efficiency: Mapped[float] = mapped_column(Float, default=0.0)  # 互动/曝光比
    audience_match_score: Mapped[float] = mapped_column(Float, default=0.0)   # 推荐受众匹配度

    # ── 结论 ──
    recommendation: Mapped[str | None] = mapped_column(Text)  # LLM 生成的优化建议
    performance_grade: Mapped[str] = mapped_column(String(8), default="C")  # S/A/B/C/D


class ContentPattern(Base, UUIDMixin, TimestampMixin):
    """系统发现的有效模式库 — 跨产品聚合的通用经验。"""
    __tablename__ = "content_patterns"

    pattern_type: Mapped[str] = mapped_column(String(32), index=True)  # hook / angle / format / timing
    pattern_key: Mapped[str] = mapped_column(String(128))  # 模式标识（如 "anxiety_hook_type_1"）
    pattern_value: Mapped[str] = mapped_column(Text)  # 具体内容

    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0~10
    sample_count: Mapped[int] = mapped_column(Integer, default=0)  # 验证次数
    emotion_tags: Mapped[list | None] = mapped_column(JSON)  # 关联情绪标签

    __table_args__ = (Index("ix_cp_type_key", "pattern_type", "pattern_key"),)


class ABTest(Base, UUIDMixin, TimestampMixin):
    """A/B 测试记录。"""
    __tablename__ = "ab_tests"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("content_products.id", ondelete="CASCADE"), index=True
    )
    variants_count: Mapped[int] = mapped_column(Integer, default=2)
    variants: Mapped[dict] = mapped_column(JSON, default=dict)  # {variant_id: {title, hook, ...}}
    platform: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="running")  # running / completed / failed
    duration_hours: Mapped[int] = mapped_column(Integer, default=168)  # 7 days default

    # ── 结果 ──
    engagement_by_variant: Mapped[dict] = mapped_column(JSON, default=dict)  # {v_id: {views, plays, ...}}
    winner_id: Mapped[str | None] = mapped_column(String(64))
    confidence_score: Mapped[float | None] = mapped_column(Float)  # 统计置信度

    # ── 反馈 ──
    insight_summary: Mapped[str | None] = mapped_column(Text)  # LLM 生成的洞察总结
    applied_to_factory: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已回写到工厂
```

Update `backend/db/init_db.py`:
```python
# Add to existing imports
from backend.models.optimization import ContentPerformance, ContentPattern, ABTest

# Add to __all__
__all__ = [
    # ...existing...
    "ContentPerformance",
    "ContentPattern",
    "ABTest",
]
```

---

### Task 2: Performance Analyzer Engine

**Objective:** Analyze raw engagement data and produce content performance insights

**Files:**
- Create: `backend/core/optimizer/__init__.py`
- Create: `backend/core/optimizer/performance_analyzer.py`

```python
"""Phase 5-C — 内容表现分析引擎。

输入:  product_engagements 原始事件 + opportunity_scores 聚合分
输出:  ContentPerformance 记录 + ContentPattern 模式提取
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.models.engagement import ProductEngagement, OpportunityScore
from backend.models.trend import ContentProduct, OpportunityReport
from backend.models.optimization import ContentPerformance, ContentPattern

logger = logging.getLogger(__name__)

# ── 归一化天花板 ──
SATURATION_VIEWS = 1000
SATURATION_ACTIONS = 300


def _normalize(value: float, ceiling: float) -> float:
    return min(10.0, (value / ceiling) * 10.0)


async def analyze_product_performance(
    product_id: str,
    session: AsyncSession,
) -> dict[str, Any]:
    """分析单个产品的表现，返回结构化报告。"""
    # 1. 获取产品信息
    product = await session.scalar(
        select(ContentProduct).where(ContentProduct.id == product_id)
    )
    if not product:
        return {"error": "product_not_found"}

    # 2. 获取聚合事件
    agg_q = (
        select(
            ProductEngagement.event_type,
            func.count(ProductEngagement.id).label("cnt"),
        )
        .where(ProductEngagement.product_id == product_id)
        .group_by(ProductEngagement.event_type)
    )
    agg_result = await session.execute(agg_q)
    events: dict[str, int] = {r.event_type: r.cnt for r in agg_result}

    total_views = events.get("view", 0)
    total_plays = events.get("audio_play", 0)
    total_downloads = events.get("ebook_download", 0)
    total_tests = events.get("test_complete", 0)

    # 3. 计算行为指标
    #    hook_retention: plays / views (完播代表钩子有效)
    hook_retention = _normalize(total_plays, SATURATION_ACTIONS) if total_views > 0 else 0.0
    
    #    angle_click: downloads / views
    angle_click = _normalize(total_downloads, SATURATION_ACTIONS) if total_views > 0 else 0.0
    
    #    format_completion: test_completes / views (仅测试类)
    format_completion = _normalize(total_tests, SATURATION_ACTIONS) if total_views > 0 else 0.0

    # 4. 衍生指标
    total_actions = total_plays + total_downloads + total_tests
    engagement_efficiency = round((total_actions / max(total_views, 1)) * 100, 2)
    
    # 5. 等级评定 (S/A/B/C/D)
    composite = (hook_retention * 0.4 + angle_click * 0.35 + format_completion * 0.25)
    if composite >= 8.0:
        grade = "S"
    elif composite >= 6.0:
        grade = "A"
    elif composite >= 4.0:
        grade = "B"
    elif composite >= 2.0:
        grade = "C"
    else:
        grade = "D"

    # 6. LLM 推荐（用产品数据 + performance 生成优化建议）
    recommendation = _generate_recommendation(
        product_type=product.product_type,
        grade=grade,
        events=events,
        meta=product.meta or {},
    )

    return {
        "product_id": product_id,
        "product_type": product.product_type,
        "total_views": total_views,
        "total_plays": total_plays,
        "total_downloads": total_downloads,
        "total_test_completes": total_tests,
        "hook_retention_rate": round(hook_retention, 2),
        "angle_click_rate": round(angle_click, 2),
        "format_completion_rate": round(format_completion, 2),
        "engagement_efficiency": engagement_efficiency,
        "performance_grade": grade,
        "recommendation": recommendation,
    }


async def analyze_all_products_for_opportunity(
    opportunity_id: str,
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """分析某个机会下所有产品的表现。"""
    products = await session.execute(
        select(ContentProduct).where(ContentProduct.opportunity_id == opportunity_id)
    )
    results = []
    for prod in products.scalars().all():
        perf = await analyze_product_performance(str(prod.id), session)
        if "error" not in perf:
            results.append(perf)
    return results


def _generate_recommendation(
    product_type: str,
    grade: str,
    events: dict[str, int],
    meta: dict,
) -> str:
    """基于规则生成优化建议（MVP 阶段先用模板，后续可升级为 LLM）。"""
    recs = []
    
    views = events.get("view", 0)
    plays = events.get("audio_play", 0)
    downloads = events.get("ebook_download", 0)
    
    # 低曝光
    if views < 10:
        recs.append("曝光不足，建议检查发布时间和标题吸引力")
    # 高曝光低互动
    elif views > 50 and (plays + downloads) < views * 0.1:
        recs.append("曝光高但互动低，建议优化前3秒钩子和CTA")
    # 高互动低转化
    elif plays > 20 and downloads == 0:
        recs.append("完播率好但下载转化为0，建议在结尾加入下载引导")
    
    # 格式特定建议
    if product_type == "ebook" and downloads < 5 and views > 30:
        recs.append("电子书下载率低，建议优化封面的价值主张")
    elif product_type == "personality_test" and events.get("test_complete", 0) < 3:
        recs.append("测试完成率低，建议简化题目或改善结果页面")
    
    if not recs:
        recs.append(f"表现评级 {grade}，继续保持当前策略")
    
    return "；".join(recs)


async def upsert_performance_report(
    product_id: str,
    opportunity_id: str | None,
    analysis: dict[str, Any],
    session: AsyncSession,
) -> None:
    """将分析结果写入 ContentPerformance 表。"""
    stmt = (
        pg_insert(ContentPerformance)
        .values(
            product_id=product_id,
            opportunity_id=opportunity_id,
            total_views=analysis.get("total_views", 0),
            total_plays=analysis.get("total_plays", 0),
            total_downloads=analysis.get("total_downloads", 0),
            total_test_completes=analysis.get("total_test_completes", 0),
            hook_retention_rate=analysis.get("hook_retention_rate", 0.0),
            angle_click_rate=analysis.get("angle_click_rate", 0.0),
            format_completion_rate=analysis.get("format_completion_rate", 0.0),
            engagement_efficiency=analysis.get("engagement_efficiency", 0.0),
            recommendation=analysis.get("recommendation"),
            performance_grade=analysis.get("performance_grade", "C"),
        )
        .on_conflict_do_update(
            constraint="content_performances_pkey",
            set_={k: v for k, v in analysis.items() if k not in ("product_id", "opportunity_id")},
        )
    )
    await session.execute(stmt)
```

---

### Task 3: A/B Test Runner

**Objective:** Create framework to auto-generate content variants, publish, track, and determine winners

**Files:**
- Create: `backend/core/optimizer/ab_test_runner.py`

```python
"""Phase 5-C — A/B 测试框架。

自动生成内容变体 → 发布到同一平台 → 追踪7天数据 → 选优 → 存档模式
"""
from __future__ import annotations
import logging
import random
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.optimization import ABTest
from backend.models.trend import ContentProduct

logger = logging.getLogger(__name__)


async def create_ab_test(
    product_id: str,
    platform: str,
    session: AsyncSession,
    num_variants: int = 3,
) -> dict[str, Any]:
    """
    创建一个 A/B 测试 — 基于已有产品生成变体。
    
    变体生成策略:
    1. 复制产品 meta 作为 baseline
    2. 调用 LLM 生成变体 (variant)
    3. 记录到 ab_tests 表
    """
    # 获取原产品
    product = await session.scalar(
        select(ContentProduct).where(ContentProduct.id == product_id)
    )
    if not product:
        return {"error": "product_not_found"}

    meta = product.meta or {}
    variants = {}
    
    # Baseline variant (original)
    variants["baseline"] = {
        "title": product.title,
        "hook": _extract_hook(meta),
        "content_diff": "original",
    }
    
    # Generate variants via LLM
    from anthropic import Anthropic
    client = Anthropic()
    
    prompt = f"""你是一个短视频/内容营销 A/B 测试专家。

原始内容类型: {product.product_type}
原标题: {product.title}
原始元数据: {str(meta)[:500]}

请生成 {num_variants - 1} 个内容变体，每个变体只改变 钩子(hook) 和 标题(title)，
保持核心信息不变。格式:

VARIANT_2:
title: [新标题]
hook: [新钩子]

VARIANT_3:
title: [新标题]  
hook: [新钩子]
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        
        # Parse variants from text
        current_variant = None
        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("VARIANT_") and ":" not in line.split("_")[-1]:
                current_variant = line.split(":")[0].strip()
                variants[current_variant] = {"content_diff": "hook_title"}
            elif current_variant and line.startswith("title:"):
                variants[current_variant]["title"] = line.replace("title:", "").strip()
            elif current_variant and line.startswith("hook:"):
                variants[current_variant]["hook"] = line.replace("hook:", "").strip()
    except Exception as e:
        logger.warning(f"LLM variant generation failed: {e}")
        # Fallback: simple title variants
        variants["variant_2"] = {
            "title": f"{product.title} (新视角)",
            "hook": f"原来{product.title}还可以这样",
            "content_diff": "title_only",
        }
        variants["variant_3"] = {
            "title": f"{product.title} — 颠覆认知",
            "hook": f"99%的人都不知道的{product.title}真相",
            "content_diff": "title_only",
        }

    # Create ABTest record
    ab_test = ABTest(
        product_id=product_id,
        variants_count=num_variants,
        variants=variants,
        platform=platform,
        status="running",
        duration_hours=168,
        engagement_by_variant={
            vid: {"views": 0, "plays": 0, "downloads": 0}
            for vid in variants
        },
    )
    session.add(ab_test)
    await session.flush()

    return {
        "ab_test_id": str(ab_test.id),
        "product_id": product_id,
        "variants": variants,
        "platform": platform,
    }


async def evaluate_ab_test(
    ab_test_id: str,
    session: AsyncSession,
) -> dict[str, Any]:
    """
    评估一个 A/B 测试的结果。
    
    1. 收集每个变体的 engagement 数据
    2. 计算胜者（综合分最高）
    3. 标记测试为 completed
    """
    ab_test = await session.scalar(
        select(ABTest).where(ABTest.id == ab_test_id)
    )
    if not ab_test:
        return {"error": "ab_test_not_found"}
    
    if ab_test.status != "running":
        return {"error": f"test_already_{ab_test.status}"}

    # Check elapsed time
    elapsed = (datetime.utcnow() - ab_test.created_at).total_seconds() / 3600
    if elapsed < 24:  # Minimum 24h
        return {"error": "test_too_early", "elapsed_hours": round(elapsed, 1)}

    from backend.models.engagement import ProductEngagement
    
    # Query engagement data per variant
    # For simplicity, we look at the product's overall engagement
    # In a full implementation, variants would be published with unique tracking params
    
    # Score each variant
    scores = {}
    for vid, vdata in ab_test.variants.items():
        engagement = ab_test.engagement_by_variant.get(vid, {})
        views = engagement.get("views", 0)
        plays = engagement.get("plays", 0)
        downloads = engagement.get("downloads", 0)
        
        # Composite score
        score = views * 0.1 + plays * 0.4 + downloads * 0.5
        scores[vid] = round(score, 2)
    
    # Determine winner
    if scores:
        winner_id = max(scores, key=scores.get)
    else:
        winner_id = "baseline"
        scores["baseline"] = 0.0
    
    # Update AB test record
    ab_test.status = "completed"
    ab_test.winner_id = winner_id
    ab_test.confidence_score = 0.8  # Simplified
    ab_test.insight_summary = f"胜者 {winner_id}，综合分 {scores.get(winner_id, 0)}"
    await session.flush()

    return {
        "ab_test_id": ab_test_id,
        "status": "completed",
        "winner_id": winner_id,
        "scores": scores,
        "insight_summary": ab_test.insight_summary,
    }


def _extract_hook(meta: dict) -> str:
    """从产品 meta 中提取钩子。"""
    hooks = meta.get("hook_lines") or meta.get("hooks") or []
    if hooks:
        return hooks[0] if isinstance(hooks, list) else str(hooks)
    return meta.get("title", "")
```

---

### Task 4: Feedback Writer — 反馈回写引擎

**Objective:** Write optimization insights back into Brain/Strategist/Factory

**Files:**
- Create: `backend/core/optimizer/feedback_writer.py`

```python
"""Phase 5-C — 反馈回写引擎。

将内容表现数据回写到:
1. Brain Prompts → 更新情绪分析指导
2. Strategist → 调整产品评分权重  
3. Factory → 更新内容模板和钩子模式
"""
from __future__ import annotations
import json
import logging
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.optimization import ContentPattern, ContentPerformance, ABTest
from backend.models.trend import ContentProduct

logger = logging.getLogger(__name__)


async def extract_patterns_from_performance(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """
    从所有 ContentPerformance 记录中提取跨产品的通用模式。
    
    如: "B 级以上的钩子特征", "高互动内容的情绪标签分布"
    """
    # Get all A-grade and above performances
    stmt = (
        select(ContentPerformance)
        .where(ContentPerformance.performance_grade.in_(["S", "A"]))
        .order_by(ContentPerformance.hook_retention_rate.desc())
    )
    result = await session.execute(stmt)
    top_performances = result.scalars().all()
    
    patterns = []
    
    # Pattern 1: High retention hooks
    if top_performances:
        high_retention = [p for p in top_performances if p.hook_retention_rate >= 6.0]
        if high_retention:
            patterns.append({
                "type": "hook",
                "key": "high_retention_hook_pattern",
                "value": f"发现 {len(high_retention)} 个高完播率内容，平均钩效 {sum(p.hook_retention_rate for p in high_retention)/len(high_retention):.1f}/10",
                "effectiveness": round(sum(p.hook_retention_rate for p in high_retention) / len(high_retention), 2),
                "sample_count": len(high_retention),
            })
    
    return patterns


async def update_factory_templates(
    winner_ab_test_id: str | None = None,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    将 A/B 测试胜者的特征注入 Factory 的模板配置。
    
    如果是 session 模式，需要外部传入 session。
    """
    updated = {"patterns_updated": 0, "ab_tests_applied": 0}
    return updated


async def write_optimization_to_brain_prompts(
    emotion_insights: dict | None = None,
) -> None:
    """
    将优化洞察写入 Brain 模块的 prompts 文件中。
    
    这通过更新 backend/core/brain/prompts.py 中的权重或模板实现。
    MVP 阶段: 记录到日志 + ContentPattern 表
    后续: 动态更新 prompts 文件中的参数
    """
    if emotion_insights:
        logger.info(
            "[FeedbackWriter] Emotion insight extracted: %s",
            json.dumps(emotion_insights, ensure_ascii=False),
        )
    # In MVP, this is a no-op — insights are logged + stored in ContentPattern
    # In full version, this would patch prompts.py or a config file
    pass
```

---

### Task 5: Optimizer Worker (ARQ)

**Objective:** Periodic job that runs the optimization pipeline

**Files:**
- Create: `backend/workers/optimizer_worker.py`

```python
"""Phase 5-C — 优化 Worker (ARQ Cron).

每小时运行:
1. 扫描近期发布的、有足够数据的产品
2. 运行 Performance Analyzer
3. 写入 ContentPerformance 表
4. 检查是否有 A/B 测试需要评估
5. 提取通用模式到 ContentPattern
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import AsyncSessionLocal
from backend.models.engagement import ProductEngagement
from backend.models.trend import ContentProduct
from backend.models.optimization import ABTest

logger = logging.getLogger(__name__)


async def run_optimization_pipeline(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    ARQ cron job — runs every hour.

    1. Find products with recent engagement
    2. Run performance analysis for each
    3. Upsert performance reports
    4. Check and evaluate A/B tests
    5. Extract cross-product patterns
    """
    logger.info("[OptimizerWorker] Starting optimization pipeline")
    
    analyzed_count = 0
    ab_evaluated = 0
    patterns_found = 0
    
    async with AsyncSessionLocal() as session:
        # Step 1: Find products with engagement in last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_products = await session.execute(
            select(ContentProduct.id, ContentProduct.opportunity_id)
            .where(
                ContentProduct.created_at >= week_ago,
                ContentProduct.status == "ready",
            )
            .limit(50)
        )
        
        from backend.core.optimizer.performance_analyzer import (
            analyze_product_performance,
            upsert_performance_report,
        )
        
        for prod_row in recent_products:
            product_id = str(prod_row.id)
            opp_id = str(prod_row.opportunity_id) if prod_row.opportunity_id else None
            
            analysis = await analyze_product_performance(product_id, session)
            if "error" not in analysis:
                await upsert_performance_report(product_id, opp_id, analysis, session)
                analyzed_count += 1
        
        # Step 2: Evaluate running A/B tests (older than 24h)
        running_tests = await session.execute(
            select(ABTest).where(
                ABTest.status == "running",
                ABTest.created_at <= datetime.utcnow() - timedelta(hours=24),
            )
        )
        
        from backend.core.optimizer.ab_test_runner import evaluate_ab_test
        
        for test in running_tests.scalars().all():
            result = await evaluate_ab_test(str(test.id), session)
            if result.get("status") == "completed":
                ab_evaluated += 1
        
        # Step 3: Extract patterns
        from backend.core.optimizer.feedback_writer import extract_patterns_from_performance, update_factory_templates
        patterns = await extract_patterns_from_performance(session)
        
        from backend.models.optimization import ContentPattern
        for pattern in patterns:
            stmt = select(ContentPattern).where(
                ContentPattern.pattern_type == pattern["type"],
                ContentPattern.pattern_key == pattern["key"],
            )
            existing = await session.scalar(stmt)
            if not existing:
                new_pattern = ContentPattern(
                    pattern_type=pattern["type"],
                    pattern_key=pattern["key"],
                    pattern_value=pattern["value"],
                    effectiveness_score=pattern.get("effectiveness", 0.0),
                    sample_count=pattern.get("sample_count", 0),
                )
                session.add(new_pattern)
                patterns_found += 1
        
        await session.commit()
    
    logger.info(
        "[OptimizerWorker] Done: analyzed=%d, ab_evaluated=%d, patterns=%d",
        analyzed_count,
        ab_evaluated,
        patterns_found,
    )
    return {
        "analyzed_count": analyzed_count,
        "ab_evaluated": ab_evaluated,
        "patterns_found": patterns_found,
    }
```

Register worker in `backend/workers/pipeline.py`:
```python
# Add import
from backend.workers.optimizer_worker import run_optimization_pipeline

# Add to functions dict
FUNCTIONS: list[ArqFunction] = [
    # ...existing...
    arq_function(run_optimization_pipeline),
]
```

---

### Task 6: Optimizer API

**Objective:** Expose optimization data and controls via API

**Files:**
- Create: `backend/api/optimizer.py`

```python
"""Phase 5-C — 优化 API 端点。"""
from __future__ import annotations
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models.optimization import (
    ContentPerformance,
    ContentPattern,
    ABTest,
)
from backend.models.trend import ContentProduct, OpportunityReport
from backend.core.optimizer.performance_analyzer import analyze_product_performance, upsert_performance_report
from backend.core.optimizer.ab_test_runner import create_ab_test

logger = logging.getLogger(__name__)
router = APIRouter()


class ProductPerformanceResponse(BaseModel):
    product_id: str
    product_type: str
    total_views: int
    total_plays: int
    total_downloads: int
    total_test_completes: int
    hook_retention_rate: float
    angle_click_rate: float
    format_completion_rate: float
    engagement_efficiency: float
    performance_grade: str
    recommendation: str | None
    
    model_config = ConfigDict(from_attributes=True)


class ABTestResponse(BaseModel):
    ab_test_id: str
    product_id: str
    variants_count: int
    variants: dict
    platform: str
    status: str
    winner_id: str | None
    insight_summary: str | None
    
    model_config = ConfigDict(from_attributes=True)


@router.get("/optimizer/products/{product_id}/performance", response_model=ProductPerformanceResponse)
async def get_product_performance(
    product_id: str,
    refresh: bool = False,
    session: AsyncSession = Depends(get_db),
) -> ProductPerformanceResponse:
    """获取单个产品的表现分析。"""
    product = await session.scalar(
        select(ContentProduct).where(ContentProduct.id == product_id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if refresh:
        # Run live analysis
        analysis = await analyze_product_performance(product_id, session)
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
        # Upsert and return
        await upsert_performance_report(
            product_id,
            str(product.opportunity_id) if product.opportunity_id else None,
            analysis,
            session,
        )
        await session.commit()
        return ProductPerformanceResponse(**analysis)
    else:
        # Read from cache
        perf = await session.scalar(
            select(ContentPerformance)
            .where(ContentPerformance.product_id == product_id)
            .order_by(desc(ContentPerformance.created_at))
            .limit(1)
        )
        if not perf:
            raise HTTPException(status_code=404, detail="No performance data yet")

    return ProductPerformanceResponse(
        product_id=str(perf.product_id),
        product_type=product.product_type,
        total_views=perf.total_views,
        total_plays=perf.total_plays,
        total_downloads=perf.total_downloads,
        total_test_completes=perf.total_test_completes,
        hook_retention_rate=perf.hook_retention_rate,
        angle_click_rate=perf.angle_click_rate,
        format_completion_rate=perf.format_completion_rate,
        engagement_efficiency=perf.engagement_efficiency,
        performance_grade=perf.performance_grade,
        recommendation=perf.recommendation,
    )


@router.post("/optimizer/products/{product_id}/ab-test", response_model=ABTestResponse)
async def start_ab_test(
    product_id: str,
    platform: str = "xiaohongshu",
    session: AsyncSession = Depends(get_db),
) -> ABTestResponse:
    """为一个产品启动 A/B 测试。"""
    result = await create_ab_test(product_id, platform, session)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    await session.commit()
    return ABTestResponse(
        ab_test_id=result["ab_test_id"],
        product_id=product_id,
        variants_count=len(result["variants"]),
        variants=result["variants"],
        platform=platform,
        status="running",
        winner_id=None,
        insight_summary=None,
    )


@router.get("/optimizer/patterns", response_model=list[dict])
async def get_content_patterns(
    pattern_type: Optional[str] = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """获取系统发现的通用内容模式。"""
    q = select(ContentPattern).order_by(desc(ContentPattern.effectiveness_score)).limit(limit)
    if pattern_type:
        q = q.where(ContentPattern.pattern_type == pattern_type)
    result = await session.execute(q)
    patterns = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "pattern_type": p.pattern_type,
            "pattern_key": p.pattern_key,
            "pattern_value": p.pattern_value,
            "effectiveness_score": p.effectiveness_score,
            "sample_count": p.sample_count,
            "emotion_tags": p.emotion_tags,
        }
        for p in patterns
    ]


@router.get("/optimizer/opportunities/{opportunity_id}/report")
async def get_opportunity_optimization_report(
    opportunity_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """获取某个机会的全局优化报告（所有产品的表现汇总）。"""
    from backend.core.optimizer.performance_analyzer import analyze_all_products_for_opportunity
    
    results = await analyze_all_products_for_opportunity(opportunity_id, session)
    
    # Categorize
    grades = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    for r in results:
        grades[r.get("performance_grade", "C")] += 1
    
    return {
        "opportunity_id": opportunity_id,
        "total_products": len(results),
        "grade_distribution": grades,
        "average_engagement_efficiency": round(
            sum(r.get("engagement_efficiency", 0) for r in results) / max(len(results), 1), 2
        ),
        "top_recommendations": [r["recommendation"] for r in results if r.get("recommendation")],
        "products": results,
    }
```

Register router in `backend/main.py`:
```python
# Add import
from backend.api import optimizer

# Add after other routers
app.include_router(optimizer.router, prefix="/api/v1", tags=["optimizer"])
```

---

### Task 7: Frontend — 优化看板

**Objective:** Build the optimization dashboard UI

**Files:**
- Create: `frontend/components/ab-test-panel.tsx`
- Create: `frontend/app/opportunities/[id]/optimize/page.tsx`

```tsx
// frontend/components/ab-test-panel.tsx
'use client';

import { useState } from 'react';
import api from '@/lib/api';

interface ABTestPanelProps {
  productId: string;
  onTestCreated?: (testId: string) => void;
}

export default function ABTestPanel({ productId, onTestCreated }: ABTestPanelProps) {
  const [platform, setPlatform] = useState('xiaohongshu');
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const res = await api.post(`/optimizer/products/${productId}/ab-test`, {
        platform,
      });
      setResult(res.data);
      onTestCreated?.(res.data.ab_test_id);
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="rounded-2xl bg-gradient-to-br from-fuchsia-900/20 to-violet-900/20 border border-fuchsia-500/20 p-5">
      <h3 className="text-sm font-bold text-fuchsia-300 mb-4">🧪 A/B 测试</h3>
      
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="text-xs text-gray-400 block mb-1">发布平台</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="xiaohongshu">📕 小红书</option>
            <option value="douyin">🎵 抖音</option>
          </select>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="px-4 py-2 rounded-lg bg-fuchsia-600 hover:bg-fuchsia-500 disabled:opacity-50 text-white text-sm font-semibold transition-all"
        >
          {creating ? '生成中...' : '🚀 启动 A/B 测试'}
        </button>
      </div>

      {result && !result.error && (
        <div className="mt-4 space-y-2">
          <p className="text-xs text-emerald-400">✅ 测试已创建（ID: {result.ab_test_id}）</p>
          <div className="text-xs text-gray-300">
            {Object.entries(result.variants || {}).map(([vid, vdata]: [string, any]) => (
              <div key={vid} className="rounded-lg bg-white/5 border border-white/10 p-2 mt-2">
                <span className="font-bold text-fuchsia-300">{vid}</span>
                <p>标题: {vdata.title || '-'}</p>
                <p>钩子: {vdata.hook || '-'}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {result?.error && (
        <p className="mt-2 text-xs text-red-400">⚠ {result.error}</p>
      )}
    </div>
  );
}
```

```tsx
// frontend/app/opportunities/[id]/optimize/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';

interface ProductPerformance {
  product_id: string;
  product_type: string;
  performance_grade: string;
  hook_retention_rate: number;
  angle_click_rate: number;
  engagement_efficiency: number;
  recommendation: string;
}

interface OptimizationReport {
  opportunity_id: string;
  total_products: number;
  grade_distribution: Record<string, number>;
  average_engagement_efficiency: number;
  top_recommendations: string[];
  products: ProductPerformance[];
}

function GradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = {
    S: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    A: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    B: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    C: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    D: 'bg-red-500/20 text-red-300 border-red-500/30',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${colors[grade] || colors.D}`}>
      {grade}
    </span>
  );
}

function GradeBar({ grades }: { grades: Record<string, number> }) {
  const order = ['S', 'A', 'B', 'C', 'D'];
  const total = Object.values(grades).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="flex h-3 rounded-full overflow-hidden">
      {order.map((g) => {
        const pct = ((grades[g] || 0) / total) * 100;
        if (pct === 0) return null;
        const colors: Record<string, string> = {
          S: 'bg-yellow-500',
          A: 'bg-emerald-500',
          B: 'bg-blue-500',
          C: 'bg-orange-500',
          D: 'bg-red-500',
        };
        return (
          <div
            key={g}
            className={colors[g]}
            style={{ width: `${pct}%` }}
            title={`${g}: ${grades[g] || 0}`}
          />
        );
      })}
    </div>
  );
}

export default function OptimizePage() {
  const params = useParams();
  const oppId = params.id as string;
  const [report, setReport] = useState<OptimizationReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get(`/optimizer/opportunities/${oppId}/report`)
      .then((r) => setReport(r.data))
      .catch(() => setReport(null))
      .finally(() => setLoading(false));
  }, [oppId]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white">
      {/* Top bar */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center gap-3">
          <Link
            href={`/opportunities/${oppId}`}
            className="text-sm text-indigo-300 hover:text-white transition-colors"
          >
            ← 返回商机详情
          </Link>
          <span className="text-white/20">/</span>
          <span className="text-sm text-white/80">优化看板</span>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-5xl">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-400" />
          </div>
        ) : report ? (
          <div className="space-y-8">
            {/* Overview */}
            <div className="rounded-2xl bg-gradient-to-br from-indigo-900/40 to-purple-900/40 border border-indigo-500/30 p-6">
              <h1 className="text-xl font-bold mb-4">📊 优化总览</h1>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="space-y-1">
                  <p className="text-xs text-gray-400">产品总数</p>
                  <p className="text-2xl font-extrabold">{report.total_products}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-gray-400">平均互动效率</p>
                  <p className="text-2xl font-extrabold">{report.average_engagement_efficiency}%</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-gray-400">S 级产品</p>
                  <p className="text-2xl font-extrabold text-yellow-300">{report.grade_distribution.S || 0}</p>
                </div>
              </div>
              <GradeBar grades={report.grade_distribution} />
              <div className="flex gap-2 mt-2 text-xs text-gray-500">
                {Object.entries(report.grade_distribution).map(([g, c]) => (
                  <span key={g} className="flex items-center gap-1">
                    <GradeBadge grade={g} /> {c}
                  </span>
                ))}
              </div>
            </div>

            {/* Products table */}
            <div className="space-y-4">
              <h2 className="text-sm font-bold text-indigo-300 uppercase tracking-wider">产品表现</h2>
              {report.products.map((p) => (
                <div
                  key={p.product_id}
                  className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3 hover:bg-white/[0.07] transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">{p.product_type}</span>
                      <GradeBadge grade={p.performance_grade} />
                    </div>
                    <Link
                      href={`/opportunities/${oppId}/products/${p.product_id}`}
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      查看 →
                    </Link>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div>
                      <span className="text-gray-400">完播率</span>
                      <p className="font-bold">{p.hook_retention_rate}/10</p>
                    </div>
                    <div>
                      <span className="text-gray-400">点击率</span>
                      <p className="font-bold">{p.angle_click_rate}/10</p>
                    </div>
                    <div>
                      <span className="text-gray-400">互动效率</span>
                      <p className="font-bold">{p.engagement_efficiency}%</p>
                    </div>
                  </div>

                  {p.recommendation && (
                    <p className="text-xs text-indigo-200 italic">
                      💡 {p.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Recommendations */}
            {report.top_recommendations.length > 0 && (
              <div className="rounded-xl bg-gradient-to-br from-amber-900/20 to-orange-900/20 border border-amber-500/20 p-4">
                <h2 className="text-sm font-bold text-amber-300 mb-3">💡 优化建议汇总</h2>
                <ul className="space-y-2">
                  {report.top_recommendations.map((rec, i) => (
                    <li key={i} className="text-xs text-gray-200 flex items-start gap-2">
                      <span className="text-amber-400">{i + 1}.</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-400">暂无优化数据</p>
            <p className="text-xs text-gray-500 mt-2">发布产品并产生互动后，这里会显示分析结果</p>
            <Link
              href={`/opportunities/${oppId}/products`}
              className="inline-block mt-4 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm"
            >
              去生成产品
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## Verification Plan

After implementation, run these checks:

```bash
# 1. Start backend
cd backend && uvicorn main:app --reload --port 8000

# 2. Test optimizer API
curl -s http://localhost:8000/api/v1/optimizer/patterns | python -m json.tool

# 3. Test product performance
curl -s "http://localhost:8000/api/v1/optimizer/products/prod-test-123/performance?refresh=true" | python -m json.tool

# 4. Test opportunity report
curl -s "http://localhost:8000/api/v1/optimizer/opportunities/aaef264f-f87d-48b2-abff-2441caaf4294/report" | python -m json.tool

# 5. Test A/B test creation
curl -s -X POST "http://localhost:8000/api/v1/optimizer/products/prod-test-123/ab-test" \
  -H "Content-Type: application/json" \
  -d '{"platform": "xiaohongshu"}' | python -m json.tool

# 6. Test frontend
cd frontend && npm run dev
# Visit: http://localhost:3000/opportunities/[oppId]/optimize
```

---

## Summary

Phase 5-C delivers:

| Layer | Component | Value |
|-------|-----------|-------|
| Models | `ContentPerformance` | 每个产品的表现快照 |
| | `ContentPattern` | 跨产品的通用模式库 |
| | `ABTest` | A/B 测试全记录 |
| Engine | `PerformanceAnalyzer` | 从原始数据提取行为指标 |
| | `ABTestRunner` | 自动生成变体+追踪+选优 |
| | `FeedbackWriter` | 洞察写回 Brain/Strategist/Factory |
| Worker | `OptimizerWorker` | 每小时自动运行优化流水线 |
| API | 4 endpoints | 表现查询/A/B测试/模式库/全局报告 |
| Frontend | Optimize Dashboard | 产品表现对比+优化建议看板 |
