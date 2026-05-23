import asyncio
import uuid
from datetime import datetime
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.models.trend import OpportunityReport, ContentProduct

async def main():
    async with AsyncSessionLocal() as db:
        # 1. Create OpportunityReport
        opp_id = str(uuid.uuid4())
        opp = OpportunityReport(
            id=opp_id,
            topic="AI Automation Trend",
            why_viral="High interest in AI productivity",
            core_emotions=["excitement", "curiosity"],
            core_pain_points=["manual task fatigue"],
            willingness_to_pay=8,
            product_suggestions=[{"name": "AI Agent Factory", "type": "SaaS"}],
            best_product="AI Agent Factory",
            roi_score=9.0,
            automation_score=8.5,
            seo_value=7.0,
            lifecycle="long-term",
            hook_lines=["The future is here!", "Automate everything!"],
            content_angles=["How to use AI", "ROI of AI"],
            monetization_strategy="SaaS Subscription",
            action_plan=["Build MVP", "Launch on ProductHunt"],
            audience_profile={"segment": "entrepreneurs"}
        )
        db.add(opp)

        # 2. Create ContentProduct
        prod_id = str(uuid.uuid4())
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
        print(f"SUCCESS: Created OppID={opp_id}, ProdID={prod_id}")
        print(f"PROD_ID:{prod_id}")

if __name__ == "__main__":
    asyncio.run(main())
