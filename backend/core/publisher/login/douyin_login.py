"""Phase 5D — Douyin (creator.douyin.com) QR code login via Playwright."""
from __future__ import annotations

import logging
import os
from typing import Any

from playwright.async_api import Page, async_playwright

from backend.core.publisher.login.base import LoginResult, QRLoginClient, QRLoginSession

logger = logging.getLogger(__name__)

_active_sessions: dict[str, tuple[Any, Any, Any, Any]] = {}


class DouyinLoginClient(QRLoginClient):
    platform_name = "douyin"

    LOGIN_URL = "https://creator.douyin.com/creator-micro/home"
    QR_SELECTOR = (
        "img.qrcode, canvas.qrcode, div.qrcode-wrap img, "
        "div[class*='qr'] img, div[class*='QrCode'] img"
    )
    LOGGED_IN_SELECTOR = (
        "div.user-info-wrap, span.user-name, "
        "div[class*='avatar-wrap'], div[class*='UserInfo']"
    )

    async def start_login(self, session_id: str) -> QRLoginSession:
        qr_dir = os.path.join(
            os.path.dirname(__file__), "../../../../static/qr"
        )
        os.makedirs(qr_dir, exist_ok=True)
        qr_path = os.path.join(qr_dir, f"{session_id}.png")
        static_path = f"/static/qr/{session_id}.png"

        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        _active_sessions[session_id] = (pw, browser, context, page)

        try:
            await page.goto(self.LOGIN_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # Douyin auto-redirects to login if not authenticated
            try:
                await page.wait_for_selector(
                    "img.qrcode, canvas.qrcode, div[class*='qr'] img, div[class*='QrCode'] img",
                    timeout=10000,
                )
            except Exception:
                logger.warning("[Douyin Login] QR selector wait timed out, taking full screenshot")

            qr_elem = page.locator(self.QR_SELECTOR)
            if await qr_elem.count() > 0:
                await qr_elem.first.screenshot(path=qr_path)
                logger.info(f"[Douyin Login] QR code saved: {qr_path}")
            else:
                await page.screenshot(path=qr_path)
                logger.warning("[Douyin Login] QR selector not found, saved full screenshot")

        except Exception as e:
            logger.error(f"[Douyin Login] start_login error: {e}")
            await browser.close()
            await pw.stop()
            _active_sessions.pop(session_id, None)
            raise

        return QRLoginSession(
            session_id=session_id,
            platform=self.platform_name,
            qr_image_path=static_path,
            status="pending",
        )

    async def poll_login_status(self, session_id: str) -> LoginResult:
        if session_id not in _active_sessions:
            return LoginResult(success=False, error="Session not found or expired")

        _, _, context, page = _active_sessions[session_id]

        try:
            logged_in = page.locator(self.LOGGED_IN_SELECTOR)
            if await logged_in.count() > 0:
                cookies = await context.cookies()
                cookie_dicts = [
                    {
                        "name": c["name"],
                        "value": c["value"],
                        "domain": c.get("domain", ""),
                        "path": c.get("path", "/"),
                        "expires": c.get("expires", -1),
                        "httpOnly": c.get("httpOnly", False),
                        "secure": c.get("secure", False),
                    }
                    for c in cookies
                ]
                user_info = await self._extract_user_info(page)
                return LoginResult(success=True, cookies=cookie_dicts, user_info=user_info)
            else:
                return LoginResult(success=False, error="not_yet_scanned")
        except Exception as e:
            return LoginResult(success=False, error=str(e))

    async def _extract_user_info(self, page: Page) -> dict[str, Any]:
        try:
            el = page.locator("span.user-name, div[class*='user-name'], span[class*='UserName']").first
            name = await el.inner_text() if await el.count() > 0 else "unknown"
            return {"nickname": name.strip()}
        except Exception:
            return {}

    async def close(self, session_id: str) -> None:
        if session_id in _active_sessions:
            pw, browser, context, page = _active_sessions.pop(session_id)
            try:
                await browser.close()
                await pw.stop()
            except Exception as e:
                logger.warning(f"[Douyin Login] close error: {e}")
