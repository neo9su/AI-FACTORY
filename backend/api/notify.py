"""
Notification management API routes.

Endpoints:
  POST /notify/test        — Send a test notification to verify QQBot config
  GET  /notify/config      — Get current notification configuration (safe — no secrets)
"""
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.qqbot_notifier import QQBotNotifier, NotifyContext, get_notifier

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class NotifyTestRequest(BaseModel):
    """Request body for test notification."""

    message: Optional[str] = "这是一条来自 AI Software Factory 的测试通知，配置成功！🎉"
    """Custom message body."""


class NotifyTestResponse(BaseModel):
    """Response from test notification call."""

    success: bool
    mode: str  # "qqbot" | "not_configured"
    error: Optional[str] = None


class NotifyConfigResponse(BaseModel):
    """Safe representation of notification config (no secrets)."""

    qqbot_configured: bool
    channel_configured: bool
    active_mode: str  # "qqbot" | "none"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/notify/test", response_model=NotifyTestResponse)
async def test_notification(body: NotifyTestRequest) -> NotifyTestResponse:
    """
    Send a test notification to verify QQBot configuration.

    Returns:
        NotifyTestResponse: Result of the notification attempt

    Raises:
        HTTPException 400: If QQBot credentials are not configured
    """
    app_id = os.getenv("QQBOT_APP_ID", "")
    app_secret = os.getenv("QQBOT_APP_SECRET", "")

    if not app_id or not app_secret:
        raise HTTPException(
            status_code=400,
            detail=(
                "QQBot 通知未配置。请在 .env 中设置 QQBOT_APP_ID 和 QQBOT_APP_SECRET。"
            ),
        )

    notifier = get_notifier()

    ctx = NotifyContext(
        project_name="AI Software Factory",
        stage="developing",
        status="running",
        message=body.message or "测试通知",
        details={
            "触发来源": "Settings 页面 / API",
            "说明": "此消息由通知配置验证功能发送",
        },
    )

    result = await notifier.send_stage_update(ctx)

    return NotifyTestResponse(
        success=result.success,
        mode="qqbot" if notifier.enabled else "not_configured",
        error=result.error,
    )


@router.get("/notify/config", response_model=NotifyConfigResponse)
async def get_notify_config() -> NotifyConfigResponse:
    """
    Return current notification configuration status.

    No secrets are exposed — only boolean flags indicating whether each
    credential is configured.

    Returns:
        NotifyConfigResponse: Configuration status
    """
    app_id = os.getenv("QQBOT_APP_ID", "")
    app_secret = os.getenv("QQBOT_APP_SECRET", "")
    channel_id = os.getenv("QQBOT_CHANNEL_ID", "")

    qqbot_configured = bool(app_id and app_secret)
    channel_configured = bool(channel_id)

    return NotifyConfigResponse(
        qqbot_configured=qqbot_configured,
        channel_configured=channel_configured,
        active_mode="qqbot" if qqbot_configured else "none",
    )
