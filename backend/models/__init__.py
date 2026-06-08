"""Database models package."""
from backend.models.auth import (
    User,
    Team,
    TeamMembership,
    TeamProject,
    MembershipStatus,
    TeamRole,
    UserRole,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.models.project import (
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
from backend.models.trend import (
    TrendSignal,
    OpportunityReport,
    ContentProduct,
    TrendScanJob,
)
from backend.models.engagement import (
    ProductEngagement,
    OpportunityScore,
)
from backend.models.publish import PublishTask as PublishJob  # noqa: F401
from backend.models.platform_session import PlatformSession  # noqa: F401

__all__ = [
    # auth models
    "User",
    "Team",
    "TeamMembership",
    "TeamProject",
    "UserRole",
    "TeamRole",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_password_hash",
    "verify_password",
    # project models
    "Project",
    "Requirements",
    "Task",
    "AgentRun",
    "TestRun",
    "CodeReview",
    "Deployment",
    "DeliveryReport",
    "PermissionPolicy",
    # NeuroTrend models
    "TrendSignal",
    "OpportunityReport",
    "ContentProduct",
    "TrendScanJob",
    # Phase 5-A: engagement models
    "ProductEngagement",
    "OpportunityScore",
    # Phase 5-B: publish models
    "PublishJob",
    # Phase 5-D: platform session models
    "PlatformSession",
]
