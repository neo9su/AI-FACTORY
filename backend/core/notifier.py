"""
Feishu (Lark) notification module for the Autonomous AI Software Factory.

Supports:
  - Custom Bot (Webhook) — simplest, no OAuth needed
  - Feishu App Bot (tenant_access_token) — full API access

Message types supported:
  - Text
  - Interactive Card (rich formatting with colors, fields, buttons)

Environment variables:
  FEISHU_WEBHOOK_URL      — Custom Bot Webhook URL (recommended for MVP)
  FEISHU_APP_ID           — App Bot app_id   (optional, for App Bot mode)
  FEISHU_APP_SECRET       — App Bot app_secret
  FEISHU_CHAT_ID          — Target chat/group id (for App Bot)
  FEISHU_SIGN_SECRET      — Webhook signature secret (optional security)
"""

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

# Card header color themes
class CardColor(str, Enum):
    BLUE = "blue"        # info / running
    GREEN = "green"      # success / delivered
    RED = "red"          # failed / blocked
    YELLOW = "yellow"    # warning / retrying
    ORANGE = "orange"    # deploying
    PURPLE = "purple"    # planning
    GREY = "grey"        # created / neutral


# Pipeline stage -> card color mapping
STAGE_COLORS: dict[str, CardColor] = {
    "created":                CardColor.GREY,
    "requirement_analyzing":  CardColor.BLUE,
    "planning":               CardColor.PURPLE,
    "developing":             CardColor.BLUE,
    "testing":                CardColor.BLUE,
    "fixing":                 CardColor.YELLOW,
    "reviewing":              CardColor.BLUE,
    "deploying":              CardColor.ORANGE,
    "delivered":              CardColor.GREEN,
    "failed":                 CardColor.RED,
    "blocked_by_gate":        CardColor.RED,
}

# Human-readable stage labels (Chinese)
STAGE_LABELS: dict[str, str] = {
    "created":                "📋 已创建",
    "requirement_analyzing":  "🔍 需求分析中",
    "planning":               "📐 规划中",
    "developing":             "⚙️ 开发中",
    "testing":                "🧪 测试中",
    "fixing":                 "🔧 修复中",
    "reviewing":              "👀 代码审查中",
    "deploying":              "🚀 部署中",
    "delivered":              "✅ 已交付",
    "failed":                 "❌ 失败",
    "blocked_by_gate":        "🚧 被权限门禁拦截",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NotifyContext:
    """Context passed to notification methods."""
    project_id: str
    project_name: str
    stage: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    preview_url: Optional[str] = None


@dataclass
class NotifyResult:
    success: bool
    status_code: int = 0
    response_body: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Feishu Notifier
# ---------------------------------------------------------------------------

class FeishuNotifier:
    """
    Sends Feishu (Lark) notifications via Custom Bot Webhook or App Bot.

    Usage (Webhook mode — recommended):
        notifier = FeishuNotifier()
        await notifier.send_stage_update(ctx)

    Usage (App Bot mode):
        notifier = FeishuNotifier(
            app_id="cli_xxx",
            app_secret="xxx",
            chat_id="oc_xxx",
        )
        await notifier.send_stage_update(ctx)
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        sign_secret: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        # Webhook mode (Custom Bot)
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")
        self.sign_secret = sign_secret or os.getenv("FEISHU_SIGN_SECRET")

        # App Bot mode
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        self.chat_id = chat_id or os.getenv("FEISHU_CHAT_ID")

        self.timeout = timeout
        self._tenant_token: Optional[str] = None
        self._token_expire_at: float = 0.0

    # ------------------------------------------------------------------
    # Public notification API
    # ------------------------------------------------------------------

    async def send_stage_update(self, ctx: NotifyContext) -> NotifyResult:
        """Send a pipeline stage change notification."""
        color = STAGE_COLORS.get(ctx.stage, CardColor.BLUE)
        label = STAGE_LABELS.get(ctx.stage, ctx.stage)
        title = f"{label} — {ctx.project_name}"

        fields = [
            {"name": "项目 ID", "value": ctx.project_id},
            {"name": "当前阶段", "value": label},
            {"name": "详情", "value": ctx.message},
        ]
        if ctx.preview_url:
            fields.append({"name": "预览地址", "value": ctx.preview_url})
        if ctx.error:
            fields.append({"name": "错误信息", "value": f"```\n{ctx.error}\n```"})

        # Merge extra details
        for k, v in ctx.details.items():
            fields.append({"name": k, "value": str(v)})

        card = self._build_card(title=title, color=color, fields=fields)
        return await self._send_card(card)

    async def send_task_complete(
        self,
        ctx: NotifyContext,
        task_title: str,
        task_status: str,
        retry_count: int = 0,
    ) -> NotifyResult:
        """Send notification when a task completes or fails."""
        success = task_status in ("completed", "passed")
        color = CardColor.GREEN if success else CardColor.RED
        emoji = "✅" if success else "❌"
        title = f"{emoji} 任务{'完成' if success else '失败'} — {ctx.project_name}"

        fields = [
            {"name": "任务", "value": task_title},
            {"name": "状态", "value": task_status},
            {"name": "重试次数", "value": str(retry_count)},
        ]
        if ctx.error:
            fields.append({"name": "错误", "value": f"```\n{ctx.error}\n```"})

        card = self._build_card(title=title, color=color, fields=fields)
        return await self._send_card(card)

    async def send_test_result(
        self,
        ctx: NotifyContext,
        passed: int,
        failed: int,
        test_type: str = "unit",
    ) -> NotifyResult:
        """Send test run results."""
        total = passed + failed
        all_passed = failed == 0
        color = CardColor.GREEN if all_passed else CardColor.RED
        emoji = "✅" if all_passed else "❌"
        title = f"{emoji} 测试{'通过' if all_passed else '失败'} — {ctx.project_name}"

        fields = [
            {"name": "测试类型", "value": test_type},
            {"name": "通过", "value": f"{passed}/{total}"},
            {"name": "失败", "value": str(failed)},
        ]
        if ctx.error and not all_passed:
            # Show first 400 chars of error log
            excerpt = ctx.error[:400] + ("..." if len(ctx.error) > 400 else "")
            fields.append({"name": "错误摘要", "value": f"```\n{excerpt}\n```"})

        card = self._build_card(title=title, color=color, fields=fields)
        return await self._send_card(card)

    async def send_delivery_report(
        self,
        ctx: NotifyContext,
        repo_url: Optional[str] = None,
        preview_url: Optional[str] = None,
        passed_tests: int = 0,
        failed_tests: int = 0,
        known_issues: Optional[list[str]] = None,
    ) -> NotifyResult:
        """Send final delivery report notification."""
        success = failed_tests == 0
        color = CardColor.GREEN if success else CardColor.YELLOW
        title = f"🎉 交付报告 — {ctx.project_name}"

        fields = [
            {"name": "项目名称", "value": ctx.project_name},
            {"name": "最终状态", "value": "✅ 成功" if success else "⚠️ 部分通过"},
            {"name": "测试通过", "value": str(passed_tests)},
            {"name": "测试失败", "value": str(failed_tests)},
        ]
        if preview_url:
            fields.append({"name": "🌐 预览地址", "value": preview_url})
        if repo_url:
            fields.append({"name": "📦 代码仓库", "value": repo_url})
        if known_issues:
            issue_text = "\n".join(f"• {i}" for i in known_issues[:5])
            fields.append({"name": "已知问题", "value": issue_text})

        card = self._build_card(title=title, color=color, fields=fields)
        return await self._send_card(card)

    async def send_gate_blocked(
        self,
        ctx: NotifyContext,
        operation: str,
        reason: str,
    ) -> NotifyResult:
        """Send notification when permission gate blocks an operation."""
        title = f"🚧 权限门禁拦截 — {ctx.project_name}"
        fields = [
            {"name": "被拦截操作", "value": operation},
            {"name": "原因", "value": reason},
            {"name": "项目 ID", "value": ctx.project_id},
        ]
        card = self._build_card(title=title, color=CardColor.RED, fields=fields)
        return await self._send_card(card)

    async def send_text(self, text: str) -> NotifyResult:
        """Send a plain text message (quick diagnostics)."""
        payload = {"msg_type": "text", "content": {"text": text}}
        return await self._dispatch(payload)

    # ------------------------------------------------------------------
    # Card builder
    # ------------------------------------------------------------------

    def _build_card(
        self,
        title: str,
        color: CardColor,
        fields: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Build a Feishu Interactive Card payload."""
        elements = []
        for f in fields:
            elements.append(
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": False,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**{f['name']}**\n{f['value']}",
                            },
                        }
                    ],
                }
            )
            elements.append({"tag": "hr"})

        # Remove trailing <hr>
        if elements and elements[-1].get("tag") == "hr":
            elements.pop()

        # Timestamp footer
        ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        elements.append(
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": f"Autonomous AI Software Factory · {ts}"}
                ],
            }
        )

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color.value,
            },
            "elements": elements,
        }
        return {"msg_type": "interactive", "card": json.dumps(card)}

    # ------------------------------------------------------------------
    # Transport layer
    # ------------------------------------------------------------------

    async def _send_card(self, payload: dict[str, Any]) -> NotifyResult:
        """Send card via whichever transport is configured."""
        if self.webhook_url:
            return await self._send_via_webhook(payload)
        elif self.app_id and self.app_secret and self.chat_id:
            return await self._send_via_app_bot(payload)
        else:
            logger.debug(
                "Feishu notifier: no FEISHU_WEBHOOK_URL or App credentials set, skipping."
            )
            return NotifyResult(success=True, status_code=0, response_body="skipped")

    async def _dispatch(self, payload: dict[str, Any]) -> NotifyResult:
        return await self._send_card(payload)

    async def _send_via_webhook(self, payload: dict[str, Any]) -> NotifyResult:
        """Send via Feishu Custom Bot Webhook."""
        body: dict[str, Any] = dict(payload)

        # Optional HMAC-SHA256 signature (for security verification)
        if self.sign_secret:
            ts = str(int(time.time()))
            sign = self._make_signature(ts, self.sign_secret)
            body["timestamp"] = ts
            body["sign"] = sign

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    self.webhook_url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
            body_text = resp.text
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    logger.info("Feishu webhook notification sent successfully.")
                    return NotifyResult(success=True, status_code=200, response_body=body_text)
                else:
                    err = f"Feishu API error code={data.get('code')} msg={data.get('msg')}"
                    logger.warning(err)
                    return NotifyResult(success=False, status_code=200, response_body=body_text, error=err)
            else:
                err = f"HTTP {resp.status_code}"
                logger.error(f"Feishu webhook failed: {err}")
                return NotifyResult(success=False, status_code=resp.status_code, response_body=body_text, error=err)
        except Exception as exc:
            logger.exception("Feishu webhook send error")
            return NotifyResult(success=False, error=str(exc))

    async def _send_via_app_bot(self, payload: dict[str, Any]) -> NotifyResult:
        """Send via Feishu App Bot (tenant_access_token)."""
        token = await self._get_tenant_token()
        if not token:
            return NotifyResult(success=False, error="Failed to obtain tenant_access_token")

        # App Bot uses /im/v1/messages
        body = {
            "receive_id": self.chat_id,
            "msg_type": payload.get("msg_type", "interactive"),
        }
        # For interactive cards the content field must be the card JSON string
        if payload.get("msg_type") == "interactive":
            body["content"] = payload.get("card", "{}")
        else:
            body["content"] = json.dumps(payload.get("content", {}))

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    FEISHU_SEND_URL,
                    params={"receive_id_type": "chat_id"},
                    json=body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
            body_text = resp.text
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    logger.info("Feishu App Bot notification sent successfully.")
                    return NotifyResult(success=True, status_code=200, response_body=body_text)
                else:
                    err = f"Feishu API error code={data.get('code')} msg={data.get('msg')}"
                    logger.warning(err)
                    return NotifyResult(success=False, status_code=200, response_body=body_text, error=err)
            else:
                err = f"HTTP {resp.status_code}"
                return NotifyResult(success=False, status_code=resp.status_code, response_body=body_text, error=err)
        except Exception as exc:
            logger.exception("Feishu App Bot send error")
            return NotifyResult(success=False, error=str(exc))

    async def _get_tenant_token(self) -> Optional[str]:
        """Fetch (and cache) Feishu tenant_access_token."""
        now = time.time()
        if self._tenant_token and now < self._token_expire_at - 60:
            return self._tenant_token

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    FEISHU_TOKEN_URL,
                    json={"app_id": self.app_id, "app_secret": self.app_secret},
                    headers={"Content-Type": "application/json"},
                )
            data = resp.json()
            if data.get("code") == 0:
                self._tenant_token = data["tenant_access_token"]
                self._token_expire_at = now + data.get("expire", 7200)
                return self._tenant_token
            else:
                logger.error(f"Failed to get tenant_access_token: {data}")
                return None
        except Exception as exc:
            logger.exception("Failed to fetch Feishu token")
            return None

    @staticmethod
    def _make_signature(timestamp: str, secret: str) -> str:
        """Compute HMAC-SHA256 signature for Feishu Custom Bot security."""
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        import base64
        return base64.b64encode(hmac_code).decode("utf-8")


# ---------------------------------------------------------------------------
# Module-level singleton — used by Orchestrator
# ---------------------------------------------------------------------------

_default_notifier: Optional[FeishuNotifier] = None


def get_notifier() -> FeishuNotifier:
    """Return (or create) the module-level FeishuNotifier singleton."""
    global _default_notifier
    if _default_notifier is None:
        _default_notifier = FeishuNotifier()
    return _default_notifier
