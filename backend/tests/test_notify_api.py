"""
Unit tests for backend/api/notify.py (QQBot notifications)

Tests:
  - POST /api/v1/notify/test — success, not configured
  - GET  /api/v1/notify/config — config status flags
"""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.core.qqbot_notifier import NotifyResult


@pytest.fixture
def qqbot_env(monkeypatch):
    """Set QQBot env vars for testing."""
    monkeypatch.setenv("QQBOT_APP_ID", "1904060647")
    monkeypatch.setenv("QQBOT_APP_SECRET", "test-secret")
    monkeypatch.setenv("QQBOT_CHANNEL_ID", "test-channel")


class TestNotifyTestEndpoint:
    """Tests for POST /api/v1/notify/test"""

    @pytest.mark.asyncio
    async def test_returns_400_when_not_configured(self, client: AsyncClient, monkeypatch):
        """Should return 400 when QQBot credentials missing."""
        monkeypatch.delenv("QQBOT_APP_ID", raising=False)
        monkeypatch.delenv("QQBOT_APP_SECRET", raising=False)
        resp = await client.post("/api/v1/notify/test", json={})
        assert resp.status_code == 400
        assert "QQBot" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_sends_notification_success(self, client: AsyncClient, qqbot_env):
        """Should send test notification and return success."""
        mock_result = NotifyResult(success=True, error=None)
        with patch(
            "backend.api.notify.get_notifier"
        ) as mock_get:
            mock_notifier = AsyncMock()
            mock_notifier.enabled = True
            mock_notifier.send_stage_update = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_notifier

            resp = await client.post("/api/v1/notify/test", json={"message": "Hello QQBot"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["mode"] == "qqbot"

    @pytest.mark.asyncio
    async def test_returns_error_on_send_failure(self, client: AsyncClient, qqbot_env):
        """Should return success=false when notification fails."""
        mock_result = NotifyResult(success=False, error="Token expired")
        with patch(
            "backend.api.notify.get_notifier"
        ) as mock_get:
            mock_notifier = AsyncMock()
            mock_notifier.enabled = True
            mock_notifier.send_stage_update = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_notifier

            resp = await client.post("/api/v1/notify/test", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is False
            assert "Token expired" in data["error"]


class TestNotifyConfigEndpoint:
    """Tests for GET /api/v1/notify/config"""

    @pytest.mark.asyncio
    async def test_returns_none_when_not_configured(self, client: AsyncClient, monkeypatch):
        """Should return active_mode='none' when no QQBot config."""
        monkeypatch.delenv("QQBOT_APP_ID", raising=False)
        monkeypatch.delenv("QQBOT_APP_SECRET", raising=False)
        monkeypatch.delenv("QQBOT_CHANNEL_ID", raising=False)
        resp = await client.get("/api/v1/notify/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_mode"] == "none"
        assert data["qqbot_configured"] is False

    @pytest.mark.asyncio
    async def test_returns_qqbot_when_configured(self, client: AsyncClient, qqbot_env):
        """Should return active_mode='qqbot' when credentials set."""
        resp = await client.get("/api/v1/notify/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_mode"] == "qqbot"
        assert data["qqbot_configured"] is True
        assert data["channel_configured"] is True
