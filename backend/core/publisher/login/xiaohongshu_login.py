"""Phase 5D — Xiaohongshu QR code login via Playwright."""
from __future__ import annotations

import logging
import os
from typing import Any

from playwright.async_api import Page, async_playwright

from backend.core.publisher.login.base import LoginResult, QRLoginClient, QRLoginSession

logger = logging.getLogger(__name__)

# In-memory store of active browser sessions: session_id -> (pw, browser, context, page)
_active_sessions: dict[str, tuple[Any, Any, Any, Any]] = {}


class XiaohongshuLoginClient(QRLoginClient):
    platform_name = "xiaohongshu"

    LOGIN_URL = "https://www.xiaohongshu.com/explore"
    QR_SELECTOR = "img.qrcode-img, div[class*='qrcode'] img, div[class*='qr-code'] img"
    LOGGED_IN_SELECTOR = "div.user-info, a.user-nickname, div.reds-avatar, div[class*='user-avatar']"

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

            login_btn = page.locator(
                "div.login-btn, button.sign-in, a[href*='login'], "
                "div[class*='login'], span:has-text('登录')"
            )
            if await login_btn.count() > 0:
                await login_btn.first.click()
                await page.wait_for_timeout(2000)

            qr_elem = page.locator(self.QR_SELECTOR)
            if await qr_elem.count() > 0:
                await qr_elem.first.screenshot(path=qr_path)
                logger.info(f"[XHS Login] QR code saved: {qr_path}")
            else:
                await page.screenshot(path=qr_path, full_page=False)
                logger.warning("[XHS Login] QR selector not found, saved full page screenshot")

        except Exception as e:
            logger.error(f"[XHS Login] start_login error: {e}")
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
            logger.error(f"[XHS Login] poll error: {e}")
            return LoginResult(success=False, error=str(e))

    async def _extract_user_info(self, page: Page) -> dict[str, Any]:
        try:
            el = page.locator("div.user-nickname, a.user-nickname, span[class*='nickname']").first
            nickname = await el.inner_text() if await el.count() > 0 else "unknown"
            return {"nickname": nickname.strip()}
        except Exception:
            return {}

    async def close(self, session_id: str) -> None:
        if session_id in _active_sessions:
            pw, browser, context, page = _active_sessions.pop(session_id)
            try:
                await browser.close()
                await pw.stop()
            except Exception as e:
                logger.warning(f"[XHS Login] close error: {e}")
