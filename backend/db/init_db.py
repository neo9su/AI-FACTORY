"""Database initialization script."""
import asyncio

from backend.db.session import engine
from backend.models.base import Base
from backend.models.project import (  # noqa: F401 — registers tables with Base.metadata
    AgentRun,
    CodeReview,
    Deployment,
    DeliveryReport,
    PermissionPolicy,
    Project,
    Requirements,
    Task,
    TestRun,
)
from backend.models.trend import (  # noqa: F401 — registers tables with Base.metadata
    ContentProduct,
    OpportunityReport,
    TrendScanJob,
    TrendSignal,
)


async def init_db() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")


async def drop_db() -> None:
    """Drop all database tables (use with caution)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("Database tables dropped successfully!")


if __name__ == "__main__":
    print("Initializing database...")
    asyncio.run(init_db())
