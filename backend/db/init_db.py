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
    TeamProject,
    TestRun,
)
from backend.models.auth import (  # noqa: F401 — registers tables with Base.metadata
    User,
    Team,
    TeamMembership,
)
from backend.models.trend import (  # noqa: F401 — registers tables with Base.metadata
    ContentProduct,
    OpportunityReport,
    TrendScanJob,
    TrendSignal,
)
from backend.models.engagement import (  # noqa: F401 — registers tables with Base.metadata
    ProductEngagement,
    OpportunityScore,
)
from backend.models.publish import PublishTask
from backend.models.optimization import ContentPerformance, ContentPattern, ABTest  # Phase 5-C  # noqa: F401
from backend.models.platform_session import PlatformSession  # noqa: F401


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
