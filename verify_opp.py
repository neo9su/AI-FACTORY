import asyncio
from backend.db.session import AsyncSessionLocal
from backend.models.trend import OpportunityReport
from sqlalchemy import select

async def main():
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(OpportunityReport).limit(1))
            opp = result.scalar_one_or_none()
            if opp:
                print(f"FOUND_OPP:{opp.id}")
            else:
                print("NO_OPP_FOUND")
    except Exception as e:
        print(f"ERROR:{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
