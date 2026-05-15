"""
Unit tests for backend/api/notify.py

Tests:
  - POST /api/v1/notify/test — success, not configured, webhook override
  - GET  /api/v1/notify/config — config status flags
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_feishu_response(success: bool = True) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    body = {"code": 0, "msg": "success"} if success else {"code": 9499, "msg": "invalid hook"}
    resp.text = json.dumps(body)
    resp.json.return_value = body
    return resp


# ---------------------------------------------------------------------------
# POST /api/v1/notify/test
# ---------------------------------------------------------------------------


class TestNotifyTestEndpoint:
    BASE_URL = "http://test"

    @pytest.mark.asyncio
    async def test_not_configured_returns_400(self):
        """No env vars → 400 Bad Request."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=self.BASE_URL
        ) as client:
            with patch.dict("os.environ", {}, clear=False):
                # Remove Feishu env vars
                import os
                env_backup = {}
                for k in ["FEISHU_WEBHOOK_URL", "FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_CHAT_ID"]:
                    env_backup[k] = os.environ.pop(k, None)

                try:
                    resp = await client.post("/api/v1/notify/test", json={})
                finally:
                    for k, v in env_backup.items():
                        if v is not None:
                            os.environ[k] = v

        assert resp.status_code == 400
        assert "FEISHU_WEBHOOK_URL" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_url_in_body_sends_notification(self):
        """webhook_url in body → notification sent, 200 OK."""
        mock_http_resp = _mock_feishu_response(success=True)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_http_resp)
            MockClient.return_value = mock_client

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=self.BASE_URL
            ) as client:
                resp = await client.post(
                    "/api/v1/notify/test",
                    json={
                        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test",
                        "message": "单元测试验证通知",
                    },
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["mode"] == "webhook"

    @pytest.mark.asyncio
    async def test_feishu_api_error_returns_success_false(self):
        """Feishu returns error code → success=False but HTTP 200."""
        mock_http_resp = _mock_feishu_response(success=False)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_http_resp)
            MockClient.return_value = mock_client

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=self.BASE_URL
            ) as client:
                resp = await client.post(
                    "/api/v1/notify/test",
                    json={"webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/bad"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["error"] is not None

    @pytest.mark.asyncio
    async def test_custom_message_in_request(self):
        """Custom message passed in body should be accepted."""
        mock_http_resp = _mock_feishu_response(success=True)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_http_resp)
            MockClient.return_value = mock_client

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=self.BASE_URL
            ) as client:
                resp = await client.post(
                    "/api/v1/notify/test",
                    json={
                        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test",
                        "message": "自定义测试消息内容",
                    },
                )

        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# GET /api/v1/notify/config
# ---------------------------------------------------------------------------


class TestNotifyConfigEndpoint:
    BASE_URL = "http://test"

    @pytest.mark.asyncio
    async def test_config_no_env_vars(self):
        """No env vars → all false, mode=none."""
        import os
        env_backup = {}
        for k in ["FEISHU_WEBHOOK_URL", "FEISHU_SIGN_SECRET", "FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_CHAT_ID"]:
            env_backup[k] = os.environ.pop(k, None)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=self.BASE_URL
            ) as client:
                resp = await client.get("/api/v1/notify/config")
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v

        assert resp.status_code == 200
        data = resp.json()
        assert data["webhook_configured"] is False
        assert data["app_bot_configured"] is False
        assert data["active_mode"] == "none"

    @pytest.mark.asyncio
    async def test_config_with_webhook_env(self):
        """FEISHU_WEBHOOK_URL set → webhook_configured=True, mode=webhook."""
        import os
        env_backup = {}
        for k in ["FEISHU_WEBHOOK_URL", "FEISHU_SIGN_SECRET", "FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_CHAT_ID"]:
            env_backup[k] = os.environ.pop(k, None)
        os.environ["FEISHU_WEBHOOK_URL"] = "https://open.feishu.cn/open-apis/bot/v2/hook/test"

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=self.BASE_URL
            ) as client:
                resp = await client.get("/api/v1/notify/config")
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["webhook_configured"] is True
        assert data["active_mode"] == "webhook"

    @pytest.mark.asyncio
    async def test_config_with_app_bot_env(self):
        """App Bot env vars set → app_bot_configured=True, mode=app_bot."""
        import os
        env_backup = {}
        for k in ["FEISHU_WEBHOOK_URL", "FEISHU_SIGN_SECRET", "FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_CHAT_ID"]:
            env_backup[k] = os.environ.pop(k, None)

        os.environ["FEISHU_APP_ID"] = "cli_test123"
        os.environ["FEISHU_APP_SECRET"] = "secret123"
        os.environ["FEISHU_CHAT_ID"] = "oc_test456"

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url=self.BASE_URL
            ) as client:
                resp = await client.get("/api/v1/notify/config")
        finally:
            for k, v in env_backup.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

        assert resp.status_code == 200
        data = resp.json()
        assert data["app_bot_configured"] is True
        assert data["active_mode"] == "app_bot"
