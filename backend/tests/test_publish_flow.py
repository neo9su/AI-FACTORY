"""Phase 5D — Integration tests for the full publish flow.

Tests the complete pipeline:
1. QR login API (start/poll/session management)
2. Publish trigger → bundle packaging
3. PublisherService bundle building for each product type
4. Platform upload (mocked)
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.publisher.publisher_service import PublisherService


# ─── PublisherService unit tests ─────────────────────────────────────────────


class TestPublisherServiceBundleBuilding:
    """Test bundle building for each product type."""

    def setup_method(self):
        self.service = PublisherService()

    def test_bundle_video_scripts_picks_best_script(self):
        """Should select script with highest viral_potential."""
        meta = {
            "title": "测试系列",
            "series_concept": "关于焦虑的三条短视频",
            "scripts_count": 2,
            "scripts": [
                {
                    "id": 1,
                    "title": "Script A",
                    "hook_line": "你有没有...",
                    "duration_seconds": 30,
                    "format": "口播",
                    "script": [
                        {"timestamp": "0:00", "visual": "close-up", "narration": "大家好", "emotion": "neutral"}
                    ],
                    "caption": "测试标题",
                    "hashtags": ["#焦虑", "#心理", "#治愈"],
                    "viral_potential": 6.5,
                    "tts_suitable": True,
                    "bgm_style": "轻音乐",
                },
                {
                    "id": 2,
                    "title": "Script B (best)",
                    "hook_line": "这个方法...",
                    "duration_seconds": 45,
                    "format": "口播+画面",
                    "script": [
                        {"timestamp": "0:00", "visual": "text", "narration": "很多人不知道", "emotion": "surprise"}
                    ],
                    "caption": "高分脚本",
                    "hashtags": ["#生活技巧", "#自律", "#成长"],
                    "viral_potential": 9.2,
                    "tts_suitable": True,
                    "bgm_style": "节奏感强",
                },
            ],
        }

        bundle = self.service.build_bundle(
            product_id="prod-001",
            product_type="short_video_scripts",
            product_meta=meta,
            platform="douyin",
            tts_audio_urls=[{"script_id": 2, "url": "/static/audio/2.wav"}],
            cover_image_url="/static/covers/prod-001.png",
        )

        assert bundle["selected_script_id"] == 2
        assert bundle["title"] == "Script B (best)"
        assert bundle["viral_potential"] == 9.2
        assert bundle["audio_url"] == "/static/audio/2.wav"
        assert bundle["cover_image_url"] == "/static/covers/prod-001.png"
        assert bundle["platform"] == "douyin"
        assert len(bundle["hashtags"]) <= 5  # douyin limit

    def test_bundle_ebook(self):
        """Should build ebook promotion bundle."""
        meta = {
            "title": "焦虑自救指南",
            "subtitle": "30天摆脱焦虑",
            "tagline": "重新掌控你的情绪",
            "sales_page_headline": "你值得拥有平静的内心",
            "price_suggestion": "¥29.9",
            "marketing_angles": ["科学方法", "亲测有效", "30天见效"],
            "intro_sample": "在这个快节奏的时代...",
            "chapters": [],
        }

        bundle = self.service.build_bundle(
            product_id="prod-002",
            product_type="ebook",
            product_meta=meta,
            platform="xiaohongshu",
            cover_image_url="/static/covers/prod-002.png",
        )

        assert bundle["product_type"] == "ebook"
        assert bundle["title"] == "焦虑自救指南"
        assert bundle["cover_image_url"] == "/static/covers/prod-002.png"
        assert "¥29.9" in bundle["caption"]
        assert len(bundle["hashtags"]) <= 10  # xiaohongshu limit

    def test_bundle_personality_test(self):
        """Should build personality test teaser bundle."""
        meta = {
            "test_name": "你是哪种焦虑类型",
            "description": "10道题测出你的焦虑模式",
        }

        bundle = self.service.build_bundle(
            product_id="prod-003",
            product_type="personality_test",
            product_meta=meta,
            platform="tiktok",
            cover_image_url=None,
        )

        assert bundle["product_type"] == "personality_test"
        assert bundle["cover_image_url"] is None
        assert "焦虑类型" in bundle["title"]

    def test_bundle_respects_platform_hashtag_limits(self):
        """Douyin=5, XHS=10, TikTok=8."""
        meta = {
            "title": "T",
            "series_concept": "C",
            "scripts_count": 1,
            "scripts": [{
                "id": 1,
                "title": "S",
                "hook_line": "H",
                "duration_seconds": 30,
                "format": "口播",
                "script": [],
                "caption": "C",
                "hashtags": [f"#tag{i}" for i in range(20)],
                "viral_potential": 5.0,
                "tts_suitable": False,
                "bgm_style": "",
            }],
        }

        for platform, limit in [("douyin", 5), ("xiaohongshu", 10), ("tiktok", 8)]:
            bundle = self.service.build_bundle(
                product_id="x",
                product_type="short_video_scripts",
                product_meta=meta,
                platform=platform,
            )
            assert len(bundle["hashtags"]) <= limit, f"{platform} hashtag limit broken"


# ─── Login API tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestLoginAPI:
    """Test QR login endpoints."""

    async def test_start_login_unsupported_platform(self, client: AsyncClient):
        """Should reject unsupported platform."""
        resp = await client.post("/api/platform-login/start/twitter")
        assert resp.status_code == 400
        assert "Unsupported platform" in resp.json()["detail"]

    async def test_list_sessions_empty(self, client: AsyncClient):
        """Should return empty list when no sessions."""
        resp = await client.get("/api/platform-login/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("backend.core.publisher.login.get_login_client")
    async def test_start_login_xiaohongshu(self, mock_get_client, client: AsyncClient):
        """Should start XHS login and return QR image URL."""
        from backend.core.publisher.login.base import QRLoginSession

        mock_client = AsyncMock()
        mock_client.start_login = AsyncMock(
            return_value=QRLoginSession(
                session_id="test-session-123",
                platform="xiaohongshu",
                qr_image_path="/static/qr/test-session-123.png",
                status="pending",
            )
        )
        mock_get_client.return_value = mock_client

        resp = await client.post("/api/platform-login/start/xiaohongshu")
        assert resp.status_code == 200
        data = resp.json()
        assert data["platform"] == "xiaohongshu"
        assert data["status"] == "pending"
        assert "qr_image_url" in data
        assert data["session_id"]  # non-empty


# ─── Publish API tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPublishAPI:
    """Test publish flow endpoints."""

    async def test_trigger_publish_product_not_found(self, client: AsyncClient):
        """Should 404 when product doesn't exist."""
        resp = await client.post(
            "/api/v1/publish/trigger",
            json={"product_id": str(uuid.uuid4()), "platforms": ["douyin"]},
        )
        assert resp.status_code == 404

    async def test_trigger_publish_invalid_platform(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Should reject invalid platform names."""
        from backend.models.trend import ContentProduct, OpportunityReport, TrendSignal

        # Create a valid product chain
        signal = TrendSignal(title="Test Signal", source="test")
        db_session.add(signal)
        await db_session.flush()

        opp = OpportunityReport(
            trend_signal_id=signal.id,
            topic="Test Topic",
            why_viral="test",
            core_emotions=[],
            core_pain_points=[],
            product_suggestions=[],
            roi_score=7.0,
            automation_score=6.0,
        )
        db_session.add(opp)
        await db_session.flush()

        product = ContentProduct(
            opportunity_id=opp.id,
            product_type="ebook",
            status="ready",
            meta={"title": "Test Ebook"},
        )
        db_session.add(product)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/publish/trigger",
            json={"product_id": str(product.id), "platforms": ["instagram"]},
        )
        assert resp.status_code == 400
        assert "Unsupported platforms" in resp.json()["detail"]

    async def test_get_publish_jobs_empty(self, client: AsyncClient):
        """Should return empty list for unknown product."""
        resp = await client.get(f"/api/v1/publish/jobs/{uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json() == []
