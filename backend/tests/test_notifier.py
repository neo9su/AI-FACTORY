"""
Unit tests for backend/core/notifier.py

Tests use httpx.MockTransport / respx to avoid real network calls.
All async tests run via pytest-asyncio.
"""

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.core.notifier import (
    CardColor,
    FeishuNotifier,
    NotifyContext,
    NotifyResult,
    STAGE_COLORS,
    get_notifier,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_notifier(webhook_url: str = "https://mock.feishu.cn/webhook/test") -> FeishuNotifier:
    return FeishuNotifier(webhook_url=webhook_url)


def _make_ctx(**kwargs) -> NotifyContext:
    defaults = dict(
        project_id="proj-123",
        project_name="Test Project",
        stage="developing",
        message="Running tasks",
    )
    defaults.update(kwargs)
    return NotifyContext(**defaults)


def _mock_response(status_code: int = 200, body: "dict | None" = None) -> httpx.Response:
    body = body or {"code": 0, "msg": "success"}
    return httpx.Response(status_code, json=body)


# ---------------------------------------------------------------------------
# NotifyContext
# ---------------------------------------------------------------------------

class TestNotifyContext:
    def test_required_fields(self):
        ctx = _make_ctx()
        assert ctx.project_id == "proj-123"
        assert ctx.project_name == "Test Project"
        assert ctx.stage == "developing"
        assert ctx.message == "Running tasks"

    def test_optional_fields_default_none(self):
        ctx = _make_ctx()
        assert ctx.error is None
        assert ctx.preview_url is None
        assert ctx.details == {}

    def test_optional_fields_set(self):
        ctx = _make_ctx(
            error="build failed",
            preview_url="https://preview.example.com",
            details={"retry": 2},
        )
        assert ctx.error == "build failed"
        assert ctx.preview_url == "https://preview.example.com"
        assert ctx.details["retry"] == 2


# ---------------------------------------------------------------------------
# NotifyResult
# ---------------------------------------------------------------------------

class TestNotifyResult:
    def test_success(self):
        r = NotifyResult(success=True, status_code=200)
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = NotifyResult(success=False, status_code=500, error="timeout")
        assert r.success is False
        assert r.error == "timeout"


# ---------------------------------------------------------------------------
# STAGE_COLORS mapping
# ---------------------------------------------------------------------------

class TestStageColors:
    def test_all_known_stages_have_color(self):
        known_stages = [
            "created", "requirement_analyzing", "planning",
            "developing", "testing", "fixing", "reviewing",
            "deploying", "delivered", "failed", "blocked_by_gate",
        ]
        for stage in known_stages:
            assert stage in STAGE_COLORS, f"Stage '{stage}' missing from STAGE_COLORS"

    def test_failed_is_red(self):
        assert STAGE_COLORS["failed"] == CardColor.RED

    def test_delivered_is_green(self):
        assert STAGE_COLORS["delivered"] == CardColor.GREEN


# ---------------------------------------------------------------------------
# FeishuNotifier.__init__
# ---------------------------------------------------------------------------

class TestFeishuNotifierInit:
    def test_webhook_mode(self):
        n = FeishuNotifier(webhook_url="https://example.com/hook")
        assert n.webhook_url == "https://example.com/hook"
        assert n.app_id is None

    def test_app_bot_mode(self):
        # webhook_url falls back to env; if no env set it stays None
        import os
        with patch.dict("os.environ", {}, clear=False):
            # Patch out env so webhook_url defaults to None
            with patch.dict("os.environ", {"FEISHU_WEBHOOK_URL": ""}, clear=False):
                n = FeishuNotifier(app_id="cli_xxx", app_secret="sec", chat_id="oc_yyy")
        assert n.app_id == "cli_xxx"

    def test_no_config_no_crash(self):
        """Notifier with neither webhook nor app creds should not crash at init."""
        with patch.dict("os.environ", {
            "FEISHU_WEBHOOK_URL": "",
            "FEISHU_APP_ID": "",
            "FEISHU_APP_SECRET": "",
        }):
            n = FeishuNotifier()
        # app_id is either None or empty string when not configured
        assert not n.app_id


# ---------------------------------------------------------------------------
# _make_signature
# ---------------------------------------------------------------------------

class TestMakeSignature:
    def test_signature_format(self):
        secret = "mysecret"
        timestamp = str(int(time.time()))
        sig = FeishuNotifier._make_signature(timestamp, secret)
        # Should be a non-empty base64-ish string
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_signature_deterministic(self):
        secret = "mysecret"
        timestamp = "1700000000"
        sig1 = FeishuNotifier._make_signature(timestamp, secret)
        sig2 = FeishuNotifier._make_signature(timestamp, secret)
        assert sig1 == sig2

    def test_signature_changes_with_timestamp(self):
        secret = "mysecret"
        sig1 = FeishuNotifier._make_signature("1700000000", secret)
        sig2 = FeishuNotifier._make_signature("1700000001", secret)
        assert sig1 != sig2


# ---------------------------------------------------------------------------
# _build_card
# ---------------------------------------------------------------------------

class TestBuildCard:
    def test_card_has_required_keys(self):
        n = _make_notifier()
        card = n._build_card(title="Test Title", color=CardColor.BLUE, fields=[])
        assert "msg_type" in card
        assert card["msg_type"] == "interactive"
        assert "card" in card

    def test_card_color_applied(self):
        n = _make_notifier()
        card_green = n._build_card(title="T", color=CardColor.GREEN, fields=[])
        card_red   = n._build_card(title="T", color=CardColor.RED,   fields=[])
        assert "green" in json.dumps(card_green)
        assert "red"   in json.dumps(card_red)

    def test_card_contains_title(self):
        n = _make_notifier()
        card = n._build_card(title="MyAwesomeApp 阶段更新", color=CardColor.BLUE, fields=[])
        assert "MyAwesomeApp" in json.dumps(card)

    def test_card_contains_field_value(self):
        n = _make_notifier()
        card = n._build_card(
            title="T", color=CardColor.ORANGE,
            fields=[{"name": "状态", "value": "Deployment in progress"}]
        )
        assert "Deployment in progress" in json.dumps(card)

    def test_card_with_multiple_fields(self):
        n = _make_notifier()
        card = n._build_card(
            title="T", color=CardColor.RED,
            fields=[
                {"name": "错误", "value": "pytest failed: 3 errors"},
                {"name": "重试", "value": "2"},
            ]
        )
        # card["card"] is a JSON string — parse it to get actual unicode text
        inner = json.loads(card["card"])
        inner_str = json.dumps(inner, ensure_ascii=False)
        assert "pytest failed" in inner_str
        assert "重试" in inner_str

    def test_card_with_preview_url_in_fields(self):
        n = _make_notifier()
        card = n._build_card(
            title="T", color=CardColor.GREEN,
            fields=[{"name": "预览地址", "value": "https://preview.myapp.com"}]
        )
        assert "https://preview.myapp.com" in json.dumps(card)


# ---------------------------------------------------------------------------
# send_stage_update (webhook mode, mocked HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSendStageUpdate:
    async def test_success(self):
        n = _make_notifier()
        ctx = _make_ctx(stage="developing")
        mock_resp = _mock_response(200, {"code": 0})

        with patch.object(n, "_send_via_webhook", new=AsyncMock(return_value=NotifyResult(success=True, status_code=200))):
            result = await n.send_stage_update(ctx)

        assert result.success is True

    async def test_no_config_returns_failure(self):
        """Notifier with no webhook/app config should return a failed result gracefully."""
        n = FeishuNotifier()
        ctx = _make_ctx()
        result = await n.send_stage_update(ctx)
        assert result.success is False
        assert result.error is not None

    async def test_http_error_returns_failure(self):
        n = _make_notifier()
        ctx = _make_ctx()

        with patch.object(n, "_send_via_webhook", new=AsyncMock(
            return_value=NotifyResult(success=False, status_code=500, error="server error")
        )):
            result = await n.send_stage_update(ctx)

        assert result.success is False


# ---------------------------------------------------------------------------
# send_test_result
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSendTestResult:
    async def test_passed_uses_green(self):
        n = _make_notifier()
        captured = {}

        async def mock_send(payload):
            captured["payload"] = payload
            return NotifyResult(success=True, status_code=200)

        with patch.object(n, "_send_via_webhook", new=mock_send):
            result = await n.send_test_result(
                _make_ctx(stage="testing"), passed=10, failed=0, test_type="unit"
            )

        assert result.success is True
        assert "green" in json.dumps(captured.get("payload", {}))

    async def test_failed_uses_red(self):
        n = _make_notifier()
        captured = {}

        async def mock_send(payload):
            captured["payload"] = payload
            return NotifyResult(success=True, status_code=200)

        with patch.object(n, "_send_via_webhook", new=mock_send):
            result = await n.send_test_result(
                _make_ctx(stage="testing"), passed=7, failed=3, test_type="unit"
            )

        assert result.success is True
        assert "red" in json.dumps(captured.get("payload", {}))


# ---------------------------------------------------------------------------
# send_delivery_report
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSendDeliveryReport:
    async def test_sends_green_card(self):
        n = _make_notifier()
        captured = {}

        async def mock_send(payload):
            captured["payload"] = payload
            return NotifyResult(success=True, status_code=200)

        ctx = _make_ctx(stage="delivered", preview_url="https://app.example.com")
        with patch.object(n, "_send_via_webhook", new=mock_send):
            result = await n.send_delivery_report(
                ctx,
                repo_url="https://github.com/x/y",
                preview_url="https://app.example.com",
                passed_tests=30,
                failed_tests=0,
            )

        assert result.success is True
        payload_str = json.dumps(captured.get("payload", {}))
        assert "green" in payload_str
        assert "https://app.example.com" in payload_str


# ---------------------------------------------------------------------------
# send_gate_blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSendGateBlocked:
    async def test_sends_red_card(self):
        n = _make_notifier()
        captured = {}

        async def mock_send(payload):
            captured["payload"] = payload
            return NotifyResult(success=True, status_code=200)

        ctx = _make_ctx(stage="blocked_by_gate", error="production deploy requires manual approval")
        with patch.object(n, "_send_via_webhook", new=mock_send):
            result = await n.send_gate_blocked(
                ctx,
                operation="deploy_to_production",
                reason="production deploy requires manual approval",
            )

        assert result.success is True
        assert "red" in json.dumps(captured.get("payload", {}))


# ---------------------------------------------------------------------------
# send_text
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSendText:
    async def test_text_message(self):
        n = _make_notifier()

        with patch.object(n, "_dispatch", new=AsyncMock(
            return_value=NotifyResult(success=True, status_code=200)
        )):
            result = await n.send_text("Hello from Hermes")

        assert result.success is True

    async def test_empty_text_still_sends(self):
        n = _make_notifier()

        with patch.object(n, "_dispatch", new=AsyncMock(
            return_value=NotifyResult(success=True, status_code=200)
        )):
            result = await n.send_text("")

        assert result.success is True


# ---------------------------------------------------------------------------
# _send_via_webhook (real httpx mock)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSendViaWebhook:
    async def test_successful_webhook(self):
        n = _make_notifier("https://mock.feishu.cn/webhook/ok")
        payload = {"msg_type": "text", "content": {"text": "hi"}}

        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"code": 0, "msg": "success"})
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=httpx.Response(200, json={"code": 0}))
            mock_client_cls.return_value = mock_client

            result = await n._send_via_webhook(payload)

        assert result.success is True
        assert result.status_code == 200

    async def test_webhook_non_200_returns_failure(self):
        n = _make_notifier("https://mock.feishu.cn/webhook/fail")
        payload = {"msg_type": "text", "content": {"text": "hi"}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=httpx.Response(429, json={"code": 99}))
            mock_client_cls.return_value = mock_client

            result = await n._send_via_webhook(payload)

        assert result.success is False
        assert result.status_code == 429

    async def test_webhook_network_error(self):
        n = _make_notifier("https://mock.feishu.cn/webhook/error")
        payload = {"msg_type": "text", "content": {"text": "hi"}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
            mock_client_cls.return_value = mock_client

            result = await n._send_via_webhook(payload)

        assert result.success is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# get_notifier() factory
# ---------------------------------------------------------------------------

class TestGetNotifier:
    def test_returns_feishu_notifier(self):
        with patch.dict("os.environ", {"FEISHU_WEBHOOK_URL": "https://example.com/hook"}):
            n = get_notifier()
        assert isinstance(n, FeishuNotifier)

    def test_no_env_still_returns_notifier(self):
        with patch.dict("os.environ", {}, clear=True):
            # Should not raise
            n = get_notifier()
        assert isinstance(n, FeishuNotifier)
