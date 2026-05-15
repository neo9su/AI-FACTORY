"""
Notification management API routes.

Endpoints:
  POST /notify/test        — Send a test notification to verify Feishu config
  GET  /notify/config      — Get current notification configuration (safe — no secrets)
"""
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.notifier import FeishuNotifier, NotifyContext

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class NotifyTestRequest(BaseModel):
    """Request body for test notification."""

    webhook_url: Optional[str] = None
    """Override FEISHU_WEBHOOK_URL env var for this call only."""

    sign_secret: Optional[str] = None
    """Override FEISHU_SIGN_SECRET env var."""

    message: Optional[str] = "这是一条来自 AI Software Factory 的测试通知，配置成功！🎉"
    """Custom message body."""


class NotifyTestResponse(BaseModel):
    """Response from test notification call."""

    success: bool
    mode: str  # "webhook" | "app_bot" | "not_configured"
    status_code: int
    error: Optional[str] = None
    response_body: Optional[str] = None


class NotifyConfigResponse(BaseModel):
    """Safe representation of notification config (no secrets)."""

    webhook_configured: bool
    sign_secret_configured: bool
    app_bot_configured: bool
    active_mode: str  # "webhook" | "app_bot" | "none"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/notify/test", response_model=NotifyTestResponse)
async def test_notification(body: NotifyTestRequest) -> NotifyTestResponse:
    """
    Send a test notification to verify Feishu configuration.

    Uses `webhook_url` from the request body if provided, otherwise falls back
    to the FEISHU_WEBHOOK_URL environment variable.  The response includes the
    Feishu API status code so the caller can diagnose errors.

    Args:
        body: Test notification parameters (all optional)

    Returns:
        NotifyTestResponse: Result of the notification attempt

    Raises:
        HTTPException 400: If neither request body nor env var has a webhook URL
            and no App Bot credentials are configured
    """
    webhook = body.webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
    sign_secret = body.sign_secret or os.getenv("FEISHU_SIGN_SECRET")

    # Determine mode
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    chat_id = os.getenv("FEISHU_CHAT_ID")

    if not webhook and not (app_id and app_secret and chat_id):
        raise HTTPException(
            status_code=400,
            detail=(
                "Feishu 通知未配置。请在 .env 中设置 FEISHU_WEBHOOK_URL，"
                "或同时设置 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_CHAT_ID。"
            ),
        )

    notifier = FeishuNotifier(
        webhook_url=webhook,
        sign_secret=sign_secret,
        app_id=app_id,
        app_secret=app_secret,
        chat_id=chat_id,
    )

    ctx = NotifyContext(
        project_id="test-notification",
        project_name="AI Software Factory",
        stage="developing",
        message=body.message or "测试通知",
        details={
            "触发来源": "Settings 页面 / API",
            "说明": "此消息由通知配置验证功能发送",
        },
    )

    result = await notifier.send_stage_update(ctx)

    mode = "not_configured"
    if webhook:
        mode = "webhook"
    elif app_id:
        mode = "app_bot"

    return NotifyTestResponse(
        success=result.success,
        mode=mode,
        status_code=result.status_code,
        error=result.error,
        response_body=result.response_body[:500] if result.response_body else None,
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
    webhook = os.getenv("FEISHU_WEBHOOK_URL", "")
    sign_secret = os.getenv("FEISHU_SIGN_SECRET", "")
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    chat_id = os.getenv("FEISHU_CHAT_ID", "")

    webhook_configured = bool(webhook)
    app_bot_configured = bool(app_id and app_secret and chat_id)

    if webhook_configured:
        active_mode = "webhook"
    elif app_bot_configured:
        active_mode = "app_bot"
    else:
        active_mode = "none"

    return NotifyConfigResponse(
        webhook_configured=webhook_configured,
        sign_secret_configured=bool(sign_secret),
        app_bot_configured=app_bot_configured,
        active_mode=active_mode,
    )
