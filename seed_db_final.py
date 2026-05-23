import asyncio
from backend.db.session import AsyncSessionLocal
from backend.models.trend import OpportunityReport, ContentProduct
from sqlalchemy import select

async def main():
    try:
        async with AsyncSessionLocal() as db:
            # 1. Create OpportunityReport
            opp_id = "aaef264f-f87d-48b2-abff-2441caaf4294"
            opp = OpportunityReport(
                id=opp_id,
                topic="AI Automation Trend",
                why_viral="High interest in AI productivity",
                core_emotions=["exc_cite", "curiosity"],
                core_pain_points=["manual task fatigue"],
                willingness_to_pay="8",  # Must be str
                product_suggestions=[{"name": "AI Agent Factory", "type": "SaaS"}],
                best_product="AI Agent Factory",
                roi_score=9.0,          # Float
                automation_score=8.5,   # Float
                seo_value="7.0",        # Must be str!
                lifecycle="long-term",
                hook_lines=["The future is enough!", "Automate everything!"],
                content_angles=["How to use AI", "ROI of AI"],
                monetization_strategy="SaaS Subscription",
                action_plan=["Build MVP", "Launch on ProductHunt"],
                audience_profile="entrepreneurs"
            )
            db.add(opp)

            # 2. Create ContentProduct
            prod_id = "prod-test-123"
            prod = ContentProduct(
                id=prod_id,
                opportunity_id=opp_id,
                product_type="video_script",
                title="Viral AI Video Script",
                status="ready",
                meta={
                    "scripts": [
                        "Scene 1: Intro to AI automation",
                        "Scene 2: The struggle of manual work",
                        "Scene 3: The solution: NeuroTrend Factory"
                    ]
                }
            )
            db.add(prod)

            await db.commit()
            print(f"SUCCESS: Created OppID={opp_id}, ProdID={round(0,0) if False else prod_id}")
            print(f"PROD_ID:{prod_id}")
    except Exception as e:
        print(f"ERROR:{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
