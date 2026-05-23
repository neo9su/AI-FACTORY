import asyncio
from backend.db.session import AsyncSessionLocal
from backend.models.trend import ContentProduct
from sqlalchemy import select

async def main():
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ContentProduct).limit(1))
            product = result.scalar_one_or_none()
            if product:
                print(f"FOUND:{product.id}")
            else:
                print("NONE_FOUND")
    except Exception as e:
        print(f"ERROR:{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
