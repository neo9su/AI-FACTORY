"""
Unit tests for backend/core/notifier.py (FeishuNotifier).

Strategy:
  - Mock httpx.AsyncClient to avoid real network calls
  - Test Webhook mode and App Bot mode separately
  - Test each public notification method (stage_update, task_complete,
    test_result, delivery_report, gate_blocked, send_text)
  - Test no-op behavior when no credentials are configured
  - Test HMAC signature generation
  - Test tenant token caching
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.notifier import (
    CardColor,
    FeishuNotifier,
    NotifyContext,
    NotifyResult,
    STAGE_COLORS,
    STAGE_LABELS,
    get_notifier,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ctx(**kwargs) -> NotifyContext:
    defaults = dict(
        project_id="proj-123",
        project_name="Test Project",
        stage="developing",
        message="Something happened",
    )
    defaults.update(kwargs)
    return NotifyContext(**defaults)


def _mock_response(status_code: int = 200, body: Optional[dict] = None) -> MagicMock:
    """Build a mock httpx Response."""
    body = body or {"code": 0, "msg": "success"}
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(body)
    resp.json.return_value = body
    return resp


# ---------------------------------------------------------------------------
# No-op when not configured
# ---------------------------------------------------------------------------

class TestNotConfigured:
    """When no env vars are set, all calls should succeed silently (skip)."""

    @pytest.mark.asyncio
    async def test_send_stage_update_no_config(self):
        notifier = FeishuNotifier()
        result = await notifier.send_stage_update(make_ctx())
        assert result.success is True
        assert result.response_body == "skipped"

    @pytest.mark.asyncio
    async def test_send_text_no_config(self):
        notifier = FeishuNotifier()
        result = await notifier.send_text("hello")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_all_methods_no_config(self):
        notifier = FeishuNotifier()
        ctx = make_ctx()

        r1 = await notifier.send_task_complete(ctx, "Task A", "completed")
        r2 = await notifier.send_test_result(ctx, passed=10, failed=0)
        r3 = await notifier.send_delivery_report(ctx, passed_tests=10, failed_tests=0)
        r4 = await notifier.send_gate_blocked(ctx, "delete_prod", "Not allowed")

        for r in (r1, r2, r3, r4):
            assert r.success is True


# ---------------------------------------------------------------------------
# Webhook mode
# ---------------------------------------------------------------------------

class TestWebhookMode:
    WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/test-token"

    def _notifier(self, **kwargs) -> FeishuNotifier:
        return FeishuNotifier(webhook_url=self.WEBHOOK, **kwargs)

    @pytest.mark.asyncio
    async def test_send_stage_update_success(self):
        notifier = self._notifier()
        mock_resp = _mock_response(200, {"code": 0, "msg": "success"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = await notifier.send_stage_update(make_ctx(stage="planning"))

        assert result.success is True
        assert result.status_code == 200
        # Verify that post was called with the webhook URL
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[0][0] == self.WEBHOOK or call_kwargs[1].get("url") == self.WEBHOOK or self.WEBHOOK in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_send_stage_update_api_error(self):
        """Feishu returns HTTP 200 but with a non-zero code."""
        notifier = self._notifier()
        mock_resp = _mock_response(200, {"code": 9499, "msg": "invalid webhook"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = await notifier.send_stage_update(make_ctx())

        assert result.success is False
        assert "9499" in (result.error or "")

    @pytest.mark.asyncio
    async def test_send_stage_update_http_error(self):
        notifier = self._notifier()
        mock_resp = _mock_response(403, {})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = await notifier.send_stage_update(make_ctx())

        assert result.success is False
        assert result.status_code == 403

    @pytest.mark.asyncio
    async def test_send_stage_update_network_exception(self):
        notifier = self._notifier()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=ConnectionError("timeout"))
            MockClient.return_value = mock_client

            result = await notifier.send_stage_update(make_ctx())

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_send_delivery_report(self):
        notifier = self._notifier()
        mock_resp = _mock_response()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = await notifier.send_delivery_report(
                make_ctx(stage="delivered"),
                preview_url="https://staging.example.com",
                repo_url="https://github.com/org/repo",
                passed_tests=28,
                failed_tests=2,
                known_issues=["Issue A", "Issue B"],
            )

        assert result.success is True
        # Verify card payload contains key fields
        post_call = mock_client.post.call_args
        body = post_call[1].get("json") or post_call[0][1]
        card_str = body.get("card", "{}")
        card = json.loads(card_str)
        elements_text = json.dumps(card["elements"])
        assert "staging.example.com" in elements_text
        assert "Issue A" in elements_text

    @pytest.mark.asyncio
    async def test_send_gate_blocked(self):
        notifier = self._notifier()
        mock_resp = _mock_response()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = await notifier.send_gate_blocked(
                make_ctx(stage="blocked_by_gate"),
                operation="deploy_to_production",
                reason="Production deployment not allowed",
            )

        assert result.success is True
        post_call = mock_client.post.call_args
        body = post_call[1].get("json") or post_call[0][1]
        card_str = body.get("card", "{}")
        card = json.loads(card_str)
        # Header should be red for gate blocked
        assert card["header"]["template"] == CardColor.RED.value


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------

class TestSignature:
    def test_make_signature_format(self):
        ts = "1700000000"
        secret = "test-secret"
        sig = FeishuNotifier._make_signature(ts, secret)
        # Should be base64-encoded
        decoded = base64.b64decode(sig)
        assert len(decoded) == 32  # SHA256 = 32 bytes

    def test_make_signature_correctness(self):
        ts = "1700000000"
        secret = "mysecret"
        string_to_sign = f"{ts}\n{secret}"
        expected_bytes = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        expected = base64.b64encode(expected_bytes).decode("utf-8")
        assert FeishuNotifier._make_signature(ts, secret) == expected

    @pytest.mark.asyncio
    async def test_webhook_with_sign_secret_adds_fields(self):
        notifier = FeishuNotifier(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/abc",
            sign_secret="my-secret",
        )
        mock_resp = _mock_response()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            await notifier.send_text("hello")

        post_call = mock_client.post.call_args
        body = post_call[1].get("json") or post_call[0][1]
        assert "timestamp" in body
        assert "sign" in body


# ---------------------------------------------------------------------------
# App Bot mode
# ---------------------------------------------------------------------------

class TestAppBotMode:
    APP_ID = "cli_test123"
    APP_SECRET = "secret123"
    CHAT_ID = "oc_test456"

    def _notifier(self) -> FeishuNotifier:
        return FeishuNotifier(
            app_id=self.APP_ID,
            app_secret=self.APP_SECRET,
            chat_id=self.CHAT_ID,
        )

    @pytest.mark.asyncio
    async def test_send_via_app_bot_success(self):
        notifier = self._notifier()
        token_resp = _mock_response(200, {
            "code": 0,
            "tenant_access_token": "t-token-abc",
            "expire": 7200,
        })
        send_resp = _mock_response(200, {"code": 0, "msg": "success"})

        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "tenant_access_token" in url:
                return token_resp
            return send_resp

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = mock_post
            MockClient.return_value = mock_client

            result = await notifier.send_stage_update(make_ctx())

        assert result.success is True
        assert call_count == 2  # 1 for token, 1 for send

    @pytest.mark.asyncio
    async def test_token_caching(self):
        """Second call should not re-fetch the token."""
        notifier = self._notifier()
        # Manually set cached token with far-future expiry
        notifier._tenant_token = "cached-token"
        notifier._token_expire_at = time.time() + 3600

        send_resp = _mock_response(200, {"code": 0, "msg": "ok"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=send_resp)
            MockClient.return_value = mock_client

            result = await notifier.send_stage_update(make_ctx())

        assert result.success is True
        # post called once (send only, no token refresh)
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_fetch_failure(self):
        notifier = self._notifier()
        token_resp = _mock_response(200, {"code": 10003, "msg": "app not found"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=token_resp)
            MockClient.return_value = mock_client

            result = await notifier.send_stage_update(make_ctx())

        assert result.success is False
        assert "tenant_access_token" in (result.error or "")


# ---------------------------------------------------------------------------
# Card builder
# ---------------------------------------------------------------------------

class TestCardBuilder:
    def test_card_structure(self):
        notifier = FeishuNotifier()
        card = notifier._build_card(
            title="Test Title",
            color=CardColor.GREEN,
            fields=[{"name": "Key", "value": "Value"}],
        )
        assert card["msg_type"] == "interactive"
        parsed = json.loads(card["card"])
        assert parsed["header"]["title"]["content"] == "Test Title"
        assert parsed["header"]["template"] == "green"
        elements = parsed["elements"]
        assert any(
            "Key" in json.dumps(e) for e in elements
        )

    def test_card_has_footer(self):
        notifier = FeishuNotifier()
        card = notifier._build_card("T", CardColor.BLUE, [])
        parsed = json.loads(card["card"])
        last = parsed["elements"][-1]
        assert last["tag"] == "note"
        assert "Autonomous AI Software Factory" in last["elements"][0]["content"]

    def test_stage_colors_coverage(self):
        """Every defined stage should map to a CardColor."""
        for stage, color in STAGE_COLORS.items():
            assert isinstance(color, CardColor)

    def test_stage_labels_coverage(self):
        """Every defined stage should have a Chinese label."""
        for stage, label in STAGE_LABELS.items():
            assert isinstance(label, str)
            assert len(label) > 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_notifier_returns_instance(self):
        n1 = get_notifier()
        n2 = get_notifier()
        assert n1 is n2
        assert isinstance(n1, FeishuNotifier)
