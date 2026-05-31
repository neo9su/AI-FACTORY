"""NeuroTrend 种子数据脚本 — 直接注入热点信号 + 商机报告到 PostgreSQL

用法: cd ~/autonomous-ai-factory && .venv/bin/python scripts/seed_opportunities.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import os

# 确保能找到 backend 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# 直接连 DB（不用 FastAPI 依赖）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/autonomous_factory")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from backend.models.trend import TrendSignal, OpportunityReport

# ============================================================
# 种子数据
# ============================================================

SEED_DATA = [
    {
        "signal": {
            "source": "seed",
            "title": "成年人社交焦虑：为什么越长大越难交朋友",
            "url": "https://www.zhihu.com/question/social-anxiety",
            "raw_content": "工作后社交圈急剧缩小，同事只能是同事，周末想约人发现大家都在忙。微信几百人却找不到一个能聊真心话的。相亲像面试，交友像谈生意。",
            "engagement_score": 95.0,
        },
        "opportunity": {
            "topic": "成年人社交焦虑：为什么越长大越难交朋友",
            "why_viral": "Z世代和千禧一代普遍面临「社交萎缩」困境，疫情后线上社交疲劳加剧，线下社交能力退化。这个痛点触及了城市化进程中的人际关系孤岛化现象，引发强烈身份认同和焦虑共鸣。",
            "core_emotions": ["孤独感", "社交焦虑", "归属感缺失", "自我怀疑", "渴望连接"],
            "core_pain_points": [
                "工作后社交圈急剧缩小，认识新朋友的机会减少",
                "线上社交看似热闹实则空洞，缺乏深度连接",
                "成年人交友的功利化和目的化让人疲惫",
                "社恐/内向性格在职场社交中被消耗殆尽",
                "渴望真诚关系但害怕主动带来的拒绝感"
            ],
            "willingness_to_pay": "高 — 孤独经济市场规模超千亿，用户为情感连接付费意愿强",
            "product_suggestions": [
                {
                    "type": "personality_test",
                    "name": "你的社交人格类型诊断",
                    "roi_score": 92,
                    "automation_score": 95,
                    "viral_score": 90,
                    "description": "H5心理测试，判断用户的社交风格（回避型/焦虑型/安全型），附带改善建议"
                },
                {
                    "type": "ebook",
                    "name": "社恐自救指南：重新学会交朋友",
                    "roi_score": 85,
                    "automation_score": 90,
                    "viral_score": 75,
                    "description": "AI生成的电子书，提供从社交焦虑到深度连接的实操方法论"
                },
                {
                    "type": "short_video_scripts",
                    "name": "成年人社交真相系列短视频",
                    "roi_score": 88,
                    "automation_score": 80,
                    "viral_score": 92,
                    "description": "10条30-60秒短视频，每条一个扎心的社交真相，适合抖音/小红书传播"
                }
            ],
            "best_product": "personality_test",
            "roi_score": 92.0,
            "automation_score": 95.0,
            "seo_value": "高 — 社交焦虑、社恐、孤独感均为高搜索量关键词",
            "lifecycle": "长期 — 代际性的社交困境，3-5年内持续",
            "hook_lines": [
                "你微信500人，能说真心话的有几个？",
                "成年人的交友潜规则：越主动越廉价",
                "你不是社恐，你只是没找到对的社交方式"
            ],
            "content_angles": [
                "数据切入 — 调查显示76%年轻人感到孤独",
                "故事切入 — 一个北漂青年的真实社交崩溃记录",
                "科学切入 — 依恋理论解释你的社交模式"
            ],
            "monetization_strategy": {
                "primary": "免费测试引流 → PDF电子书付费下载（19.9元）",
                "secondary": "AI社交教练订阅制（月卡29.9元）",
                "viral_formula": "测试结果分享到朋友圈 → 裂变引流"
            },
            "audience_profile": "22-35岁，一二线城市白领，本科以上学历，月入8k-30k，女性略多"
        }
    },
    {
        "signal": {
            "source": "seed",
            "title": "MBTI爆火背后：年轻人为什么沉迷人格标签",
            "url": "https://www.xiaohongshu.com/search_result/mbti",
            "raw_content": "INFJ、ENTP、INTJ…万物皆可MBTI。交友软件标注人格类型，简历写MBTI，相亲先问人格。人格测试成了新一代的身份标签和社交货币。",
            "engagement_score": 92.0,
        },
        "opportunity": {
            "topic": "MBTI爆火背后：年轻人为什么沉迷人格标签",
            "why_viral": "MBTI满足了年轻人对自我认知的刚需，同时提供了简便的社交身份标签。人格测试结果易于传播和讨论，形成了巨大的社交货币效应。",
            "core_emotions": ["身份认同需求", "归属感", "自我探索欲望", "社交安全感", "独特感"],
            "core_pain_points": [
                "在身份碎片化的时代不了解自己是谁",
                "需要简单的标签降低社交复杂度",
                "缺乏自我认同和确定感",
                "在职场/恋爱中不知道如何定位自己",
                "渴望找到'同类'的归属感"
            ],
            "willingness_to_pay": "极高 — MBTI相关产品年增长率超200%，测试付费、课程、周边均畅销",
            "product_suggestions": [
                {
                    "type": "personality_test",
                    "name": "你的隐藏人格类型：荣格原型深度测评",
                    "roi_score": 95,
                    "automation_score": 95,
                    "viral_score": 93,
                    "description": "结合MBTI+荣格12原型的高级人格测试，生成专属人格卡片"
                },
                {
                    "type": "ebook",
                    "name": "人格密码：用MBTI找到最适合你的职业和爱情",
                    "roi_score": 88,
                    "automation_score": 90,
                    "viral_score": 80,
                    "description": "AI生成的16型人格职业/恋爱指南PDF"
                },
                {
                    "type": "short_video_scripts",
                    "name": "MBTI人格图鉴系列短视频",
                    "roi_score": 85,
                    "automation_score": 80,
                    "viral_score": 95,
                    "description": "16种人格类型的搞笑/扎心日常，每期一个类型"
                }
            ],
            "best_product": "personality_test",
            "roi_score": 95.0,
            "automation_score": 95.0,
            "seo_value": "极高 — MBTI/人格测试搜索量巨大",
            "lifecycle": "中长期 — MBTI热度持续3年+，人格测试是永恒需求",
            "hook_lines": [
                "测了100次MBTI，你真的了解自己吗？",
                "人格测试爆火：你不是喜欢分类，你是想被理解",
                "你的MBTI可能在骗你"
            ],
            "content_angles": [
                "娱乐切入 — 各个人格的搞笑日常",
                "科学切入 — 荣格心理学解读",
                "实用切入 — MBTI教你找对象/找工作"
            ],
            "monetization_strategy": {
                "primary": "免费基础测试 → 深度报告付费（29.9元）",
                "secondary": "人格配对社交小程序会员制",
                "viral_formula": "测试结果生成精美卡片 → 分享到社交媒体"
            },
            "audience_profile": "16-35岁，学生+职场新人，极高社交分享意愿"
        }
    },
    {
        "signal": {
            "source": "seed",
            "title": "AI时代焦虑：普通人如何避免被淘汰",
            "url": "https://www.reddit.com/r/Futurology",
            "raw_content": "GPT-5、Claude 4、AI编程…每天都有新AI工具出现。设计师被裁、程序员焦虑、翻译失业。普通人到底该怎么应对AI时代？",
            "engagement_score": 98.0,
        },
        "opportunity": {
            "topic": "AI时代焦虑：普通人如何避免被淘汰",
            "why_viral": "2025年AI加速渗透各行各业，白领阶层的职业焦虑达到顶峰。恐惧被替代的心理触发了广泛讨论和内容消费。",
            "core_emotions": ["职业焦虑", "生存恐惧", "无力感", "羡慕嫉妒", "急迫感"],
            "core_pain_points": [
                "每天看到AI新进展，不知道跟自己有什么关系",
                "害怕被优化但不知道学什么来得及",
                "AI技能门槛被营销号夸大，不知道从哪开始",
                "担心已经错过了AI红利窗口期",
                "想转型但不知道AI时代什么岗位安全"
            ],
            "willingness_to_pay": "极高 — AI焦虑经济是2025年最大风口之一",
            "product_suggestions": [
                {
                    "type": "ebook",
                    "name": "普通人AI生存指南：从零开始的AI时代护城河",
                    "roi_score": 90,
                    "automation_score": 90,
                    "viral_score": 85,
                    "description": "面向非技术人群的AI时代生存策略PDF，不讲代码，只讲思路和方法"
                },
                {
                    "type": "personality_test",
                    "name": "你的AI时代生存指数测评",
                    "roi_score": 88,
                    "automation_score": 95,
                    "viral_score": 90,
                    "description": "测试你当前的抗AI替代能力，给出个性化提升建议"
                },
                {
                    "type": "short_video_scripts",
                    "name": "AI焦虑粉碎机系列短视频",
                    "roi_score": 85,
                    "automation_score": 85,
                    "viral_score": 92,
                    "description": "每天一条60秒AI新闻解读，让普通人也能看懂AI趋势"
                }
            ],
            "best_product": "ebook",
            "roi_score": 90.0,
            "automation_score": 90.0,
            "seo_value": "极高 — AI焦虑/AI替代/AI时代等搜索量爆发增长",
            "lifecycle": "中长期 — AI焦虑将持续3-5年",
            "hook_lines": [
                "AI不会淘汰人类，但会用AI的人会淘汰不用的人",
                "你的工作5年内还在吗？",
                "真正的铁饭碗不是岗位，是适应力"
            ],
            "content_angles": [
                "恐惧切入 — X个即将被AI取代的职业",
                "希望切入 — AI时代最安全的N个职业",
                "行动切入 — 每天15分钟的AI学习计划"
            ],
            "monetization_strategy": {
                "primary": "免费电子书引流 → AI工具合集付费包（39.9元）",
                "secondary": "AI学习社群订阅（月卡19.9元）",
                "viral_formula": "焦虑感驱动转发 → '快来看看你的工作会不会被替代'"
            },
            "audience_profile": "25-45岁，白领/职场人/创业者，有焦虑但愿意行动"
        }
    },
    {
        "signal": {
            "source": "seed",
            "title": "年轻人为什么不想谈恋爱了",
            "url": "https://www.zhihu.com/question/relationship-trends",
            "raw_content": "恋爱成本越来越高，约会要花钱、过节要送礼、结婚要房子。与其在感情里内耗，不如一个人舒服。Z世代的恋爱意愿创历史新低。",
            "engagement_score": 90.0,
        },
        "opportunity": {
            "topic": "年轻人为什么不想谈恋爱了",
            "why_viral": "触及了Z世代情感关系中的核心矛盾：渴望亲密又害怕付出。经济压力下移、个体意识崛起、社交媒体制造完美恋爱的焦虑，形成多重情绪叠加。",
            "core_emotions": ["情感倦怠", "经济焦虑", "孤独但逃避", "浪漫渴望", "自我防御"],
            "core_pain_points": [
                "恋爱成本过高（约会/礼物/节日/旅游=经济压力）",
                "害怕在感情中受伤和浪费时间",
                "社交媒体上的'完美恋情'制造不切实际的期待",
                "工作已经耗尽社交精力，没力气经营关系",
                "独处太舒服，失去了为别人调整的意愿"
            ],
            "willingness_to_pay": "高 — 情感陪伴/自我提升/恋爱指导类产品付费意愿强",
            "product_suggestions": [
                {
                    "type": "personality_test",
                    "name": "你的恋爱人格与理想伴侣匹配测试",
                    "roi_score": 90,
                    "automation_score": 95,
                    "viral_score": 92,
                    "description": "H5测试分析用户的恋爱模式（回避/焦虑/安全型），输出理想伴侣画像"
                },
                {
                    "type": "ebook",
                    "name": "独处也是一种能力：高质量单身生活指南",
                    "roi_score": 82,
                    "automation_score": 90,
                    "viral_score": 75,
                    "description": "不是催你谈恋爱，而是教你把一个人的生活过好"
                },
                {
                    "type": "short_video_scripts",
                    "name": "当代恋爱图鉴系列短视频",
                    "roi_score": 85,
                    "automation_score": 80,
                    "viral_score": 93,
                    "description": "10条'年轻人的恋爱现状'扎心纪实风格短视频"
                }
            ],
            "best_product": "personality_test",
            "roi_score": 90.0,
            "automation_score": 95.0,
            "seo_value": "高 — '不谈恋爱'/'单身'/'恋爱焦虑'搜索量高",
            "lifecycle": "长期 — 代际性现象，将持续多年",
            "hook_lines": [
                "不是不想谈恋爱，是不敢",
                "第一批00后已经决定不结婚了",
                "高质量的独处胜过低质量的恋爱"
            ],
            "content_angles": [
                "数据切入 — Z世代恋爱意愿下降XX%",
                "故事切入 — '我选择单身3年后的生活变化'",
                "心理切入 — 回避型依恋是怎么形成的"
            ],
            "monetization_strategy": {
                "primary": "测试引流 → 恋爱/独处指南PDF（14.9元）",
                "secondary": "AI情感日记订阅制（月卡9.9元）",
                "viral_formula": "测试结果Tag → 朋友圈/小红书晒图"
            },
            "audience_profile": "18-30岁，单身/对恋爱持观望态度，女性偏多，一线城市"
        }
    },
    {
        "signal": {
            "source": "seed",
            "title": "副业焦虑：打工人如何找到第二收入来源",
            "url": "https://www.xiaohongshu.com/topic/side-hustle",
            "raw_content": "月薪5000房租3000，不搞副业根本活不下去。AI时代给了每个人搞副业的机会，但信息太多不知道从哪开始。小红书/抖音上副业博主最火的赛道。",
            "engagement_score": 93.0,
        },
        "opportunity": {
            "topic": "副业焦虑：打工人如何找到第二收入来源",
            "why_viral": "经济下行周期中，副业从'可选项'变成了'必需品'。AI工具降低了副业门槛，但信息过载又制造了新的焦虑。副业话题在小红书/抖音的讨论量级过亿。",
            "core_emotions": ["经济焦虑", "向上挣扎", "不甘平庸", "嫉妒同行", "急功近利"],
            "core_pain_points": [
                "主业收入不够花，但不知道做什么副业",
                "副业信息太多，被各种'月入过万'的案例制造焦虑",
                "试过几个副业没赚到钱就放弃了",
                "时间精力有限，不知道哪个副业ROI最高",
                "害怕副业投入了时间结果一场空"
            ],
            "willingness_to_pay": "极高 — 副业韭菜经济，'教你赚钱'是最好卖的产品",
            "product_suggestions": [
                {
                    "type": "ebook",
                    "name": "2025副业掘金地图：AI时代的20个低门槛赚钱方式",
                    "roi_score": 92,
                    "automation_score": 90,
                    "viral_score": 88,
                    "description": "每个副业包含：门槛/收入预期/启动时间/风险评级/AI工具推荐"
                },
                {
                    "type": "personality_test",
                    "name": "你的副业人格：什么类型的副业最适合你",
                    "roi_score": 85,
                    "automation_score": 95,
                    "viral_score": 88,
                    "description": "根据性格/技能/时间/风险偏好匹配最适合的副业方向"
                },
                {
                    "type": "short_video_scripts",
                    "name": "AI副业实操系列短视频",
                    "roi_score": 88,
                    "automation_score": 85,
                    "viral_score": 90,
                    "description": "每条展示一个AI+副业的实操案例，从0到1完整流程"
                }
            ],
            "best_product": "ebook",
            "roi_score": 92.0,
            "automation_score": 90.0,
            "seo_value": "极高 — 副业/搞钱/第二收入/被动收入均为高搜索量词",
            "lifecycle": "长期 — 经济下行周期中副业需求将持续增长",
            "hook_lines": [
                "你的副业不是不够努力，是方向错了",
                "月薪5000和月入5万的人，差距在哪？",
                "2025年最值得做的5个AI副业"
            ],
            "content_angles": [
                "痛点切入 — 副业踩坑血泪史",
                "实操切入 — 从0开始做XX副业全流程",
                "对比切入 — 这5种副业千万别做vs这3个最推荐"
            ],
            "monetization_strategy": {
                "primary": "副业地图PDF引流（9.9元）→ 进阶课程（199元）",
                "secondary": "AI副业工具包/模板合集",
                "viral_formula": "副业收入截图 → 小红书/抖音爆款文案"
            },
            "audience_profile": "22-35岁，收入5k-15k，有副业想法但没行动，男女均衡"
        }
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        # 检查是否已经有 seed 来源的数据
        result = await session.execute(
            select(TrendSignal).where(TrendSignal.source == "seed").limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print("⚠️ 种子数据已存在，跳过注入（先删除再重跑）")
            print(f"   执行 DELETE 确认: .venv/bin/python -c \"from scripts.seed_opportunities import cleanup; import asyncio; asyncio.run(cleanup())\"")
            return

        created_opps = []

        for item in SEED_DATA:
            # 1. 创建 TrendSignal
            sig = item["signal"]
            signal = TrendSignal(
                source=sig["source"],
                title=sig["title"],
                url=sig.get("url"),
                raw_content=sig.get("raw_content"),
                engagement_score=sig["engagement_score"],
                viral_score=sig["engagement_score"] * 0.85,
                analyzed=True,
                emotion_tags=item["opportunity"]["core_emotions"],
                pain_points=item["opportunity"]["core_pain_points"],
            )
            session.add(signal)
            await session.flush()

            # 2. 创建 OpportunityReport
            opp = item["opportunity"]
            report = OpportunityReport(
                trend_signal_id=signal.id,
                topic=opp["topic"],
                why_viral=opp["why_viral"],
                core_emotions=opp["core_emotions"],
                core_pain_points=opp["core_pain_points"],
                willingness_to_pay=opp["willingness_to_pay"],
                product_suggestions=opp["product_suggestions"],
                best_product=opp["best_product"],
                roi_score=opp["roi_score"],
                automation_score=opp["automation_score"],
                seo_value=opp.get("seo_value"),
                lifecycle=opp.get("lifecycle"),
                hook_lines=opp.get("hook_lines", []),
                content_angles=opp.get("content_angles", []),
                monetization_strategy=opp.get("monetization_strategy"),
                audience_profile=opp.get("audience_profile", ""),
            )
            session.add(report)
            created_opps.append(report)

        await session.commit()

        print(f"✅ 成功注入 {len(SEED_DATA)} 组种子数据:")
        for r in created_opps:
            print(f"  📊 [{r.roi_score:5.1f}] {r.topic[:40]}")
            print(f"        ID: {r.id}")
            print(f"        产品建议: {[p['type'] for p in r.product_suggestions]}")
        print()
        print("🌐 访问 http://localhost:3000/opportunities 查看")
        print("📌 在商机卡片上点击 '生成产品' 触发 AI Factory 生产")


async def cleanup():
    """删除所有 seed 来源的数据"""
    async with AsyncSessionLocal() as session:
        signals = await session.execute(
            select(TrendSignal).where(TrendSignal.source == "seed")
        )
        for s in signals.scalars().all():
            await session.delete(s)
        await session.commit()
        print(f"✅ 已清理所有 seed 数据")


if __name__ == "__main__":
    asyncio.run(seed())
