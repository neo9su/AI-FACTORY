"""
QQ Bot notification module for the Autonomous AI Software Factory.

Uses QQ Bot HTTP API to send project status notifications.
QQ 机器人官方 API 文档: https://bot.q.qq.com/wiki/develop/api-v2/

Environment variables:
  QQBOT_APP_ID        — QQ Bot App ID
  QQBOT_APP_SECRET    — QQ Bot App Secret
  QQBOT_CHANNEL_ID    — Target channel ID for notifications (optional)
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# QQ Bot API endpoints
QQBOT_API_BASE = "https://api.sgroup.qq.com"
QQBOT_SANDBOX_API_BASE = "https://sandbox.api.sgroup.qq.com"
QQBOT_TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"


class CardColor(str, Enum):
    """Color themes for notifications."""
    BLUE = "blue"
    GREEN = "green"
    RED = "red"
    YELLOW = "yellow"
    ORANGE = "orange"
    PURPLE = "purple"
    GREY = "grey"


@dataclass
class NotifyContext:
    """Context for a notification event (matches old FeishuNotifier interface)."""
    project_id: str = ""
    project_name: str = ""
    stage: str = ""
    message: str = ""
    details: dict = field(default_factory=dict)
    error: Optional[str] = None
    preview_url: Optional[str] = None
    color: CardColor = CardColor.BLUE
    status: str = ""  # running / success / failed / blocked (optional)


@dataclass
class NotifyResult:
    """Result of sending a notification."""
    success: bool
    error: Optional[str] = None
    response_data: Optional[dict] = None


class QQBotNotifier:
    """
    QQ Bot notifier that provides the same interface as FeishuNotifier.
    
    Uses QQ Bot's HTTP API to send messages to channels/groups.
    """

    def __init__(self) -> None:
        self.app_id = os.getenv("QQBOT_APP_ID", "")
        self.app_secret = os.getenv("QQBOT_APP_SECRET", "")
        self.channel_id = os.getenv("QQBOT_CHANNEL_ID", "")
        self.sandbox = os.getenv("QQBOT_SANDBOX", "false").lower() == "true"
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        
        self.api_base = QQBOT_SANDBOX_API_BASE if self.sandbox else QQBOT_API_BASE
        
        if not self.app_id or not self.app_secret:
            logger.warning("QQBOT_APP_ID or QQBOT_APP_SECRET not set; notifications disabled")

    @property
    def enabled(self) -> bool:
        return bool(self.app_id and self.app_secret)

    async def _get_access_token(self) -> Optional[str]:
        """Get or refresh QQ Bot access token."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    QQBOT_TOKEN_URL,
                    json={
                        "appId": self.app_id,
                        "clientSecret": self.app_secret,
                    },
                )
                data = resp.json()
                if "access_token" in data:
                    self._access_token = data["access_token"]
                    self._token_expires_at = time.time() + int(data.get("expires_in", 7200)) - 60
                    return self._access_token
                else:
                    logger.error(f"QQBot token error: {data}")
                    return None
        except Exception as e:
            logger.error(f"QQBot token request failed: {e}")
            return None

    def _format_stage_message(self, ctx: NotifyContext) -> str:
        """Format stage update as markdown message."""
        status_emoji = {
            "running": "🔄",
            "success": "✅",
            "failed": "❌",
            "blocked": "⚠️",
        }
        status = ctx.status or ctx.stage or "info"
        emoji = status_emoji.get(status, "ℹ️")
        
        lines = [
            f"{emoji} **{ctx.project_name}**",
            f"",
            f"**阶段:** {ctx.stage}",
        ]
        
        if ctx.status:
            lines.append(f"**状态:** {ctx.status.upper()}")
        
        if ctx.message:
            lines.append(f"**信息:** {ctx.message}")
        
        if ctx.error:
            lines.append(f"**错误:** {ctx.error}")
        
        if ctx.details:
            lines.append("")
            for k, v in ctx.details.items():
                lines.append(f"• {k}: {v}")
        
        return "\n".join(lines)

    async def send_stage_update(self, ctx: NotifyContext) -> NotifyResult:
        """Send a project stage update notification."""
        msg = self._format_stage_message(ctx)
        return await self._send_message(msg)

    async def send_task_complete(
        self,
        ctx_or_name,
        task_title: str = "",
        task_name: str = "",
        task_status: str = "completed",
        duration: float = 0,
        files_changed: int = 0,
        retry_count: int = 0,
    ) -> NotifyResult:
        """Send task completion notification."""
        if isinstance(ctx_or_name, NotifyContext):
            project_name = ctx_or_name.project_name
        else:
            project_name = ctx_or_name
        
        title = task_title or task_name
        emoji = "✅" if task_status in ("completed", "passed") else "❌"
        msg = (
            f"{emoji} **任务{'完成' if task_status in ('completed', 'passed') else '失败'}**\n\n"
            f"**项目:** {project_name}\n"
            f"**任务:** {title}\n"
            f"**状态:** {task_status}\n"
            f"**重试次数:** {retry_count}"
        )
        if duration:
            msg += f"\n**耗时:** {duration:.1f}s"
        if files_changed:
            msg += f"\n**文件变更:** {files_changed}"
        return await self._send_message(msg)

    async def send_test_result(
        self,
        ctx_or_name,
        passed: int = 0,
        failed: int = 0,
        total: int = 0,
        coverage: float = 0.0,
        test_type: str = "",
    ) -> NotifyResult:
        """Send test result notification."""
        if isinstance(ctx_or_name, NotifyContext):
            project_name = ctx_or_name.project_name
            # Try to parse from message if not provided
            if not total and ctx_or_name.message:
                pass  # Use provided params
        else:
            project_name = ctx_or_name
        
        emoji = "✅" if failed == 0 else "❌"
        msg = (
            f"{emoji} **测试结果**\n\n"
            f"**项目:** {project_name}\n"
            f"**通过:** {passed}/{total}\n"
            f"**失败:** {failed}"
        )
        if coverage:
            msg += f"\n**覆盖率:** {coverage:.1f}%"
        return await self._send_message(msg)

    async def send_delivery_report(
        self,
        ctx_or_name,
        repo_url: str = "",
        deploy_url: str = "",
        summary: str = "",
        preview_url: str = None,
        passed_tests: int = 0,
        failed_tests: int = 0,
        known_issues: list = None,
    ) -> NotifyResult:
        """Send delivery report notification."""
        if isinstance(ctx_or_name, NotifyContext):
            project_name = ctx_or_name.project_name
        else:
            project_name = ctx_or_name
        
        lines = [f"🎉 **项目交付**\n", f"**项目:** {project_name}"]
        if repo_url:
            lines.append(f"**仓库:** {repo_url}")
        if deploy_url or preview_url:
            lines.append(f"**部署:** {deploy_url or preview_url}")
        if passed_tests:
            lines.append(f"**测试通过:** {passed_tests}")
        if failed_tests:
            lines.append(f"**测试失败:** {failed_tests}")
        if known_issues:
            lines.append(f"**已知问题:** {', '.join(known_issues[:3])}")
        if summary:
            lines.append(f"\n{summary}")
        return await self._send_message("\n".join(lines))

    async def send_gate_blocked(
        self,
        ctx_or_name,
        reason: str = "",
        action_required: str = "",
        operation: str = "",
    ) -> NotifyResult:
        """Send gate-blocked notification."""
        if isinstance(ctx_or_name, NotifyContext):
            project_name = ctx_or_name.project_name
            if not reason:
                reason = ctx_or_name.message
        else:
            project_name = ctx_or_name
        
        msg = (
            f"⚠️ **流程阻塞**\n\n"
            f"**项目:** {project_name}\n"
            f"**原因:** {reason}"
        )
        if operation:
            msg += f"\n**操作:** {operation}"
        if action_required:
            msg += f"\n**需要操作:** {action_required}"
        return await self._send_message(msg)

    async def send_text(self, text: str) -> NotifyResult:
        """Send a plain text message."""
        return await self._send_message(text)

    async def _send_message(self, content: str) -> NotifyResult:
        """Send message via QQ Bot API."""
        if not self.enabled:
            logger.debug("QQBot notifications disabled (no credentials)")
            return NotifyResult(success=False, error="QQBot not configured")

        token = await self._get_access_token()
        if not token:
            return NotifyResult(success=False, error="Failed to get QQBot access token")

        # If no channel configured, just log
        if not self.channel_id:
            logger.info(f"QQBot notification (no channel): {content[:100]}")
            return NotifyResult(success=True, error="No channel configured, logged only")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.api_base}/channels/{self.channel_id}/messages",
                    headers={
                        "Authorization": f"QQBotAccessToken {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "content": content,
                        "msg_type": 0,  # text type
                    },
                )
                
                if resp.status_code in (200, 201, 204):
                    return NotifyResult(success=True, response_data=resp.json() if resp.text else {})
                else:
                    error_msg = f"QQBot API error: {resp.status_code} - {resp.text[:200]}"
                    logger.error(error_msg)
                    return NotifyResult(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"QQBot send failed: {e}"
            logger.error(error_msg)
            return NotifyResult(success=False, error=error_msg)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_default_notifier: Optional[QQBotNotifier] = None


def get_notifier() -> QQBotNotifier:
    """Return (or create) the module-level QQBotNotifier singleton."""
    global _default_notifier
    if _default_notifier is None:
        _default_notifier = QQBotNotifier()
    return _default_notifier
