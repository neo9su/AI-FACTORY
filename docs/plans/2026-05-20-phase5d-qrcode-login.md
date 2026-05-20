# Phase 5D — 扫码登录实现计划

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 用 Playwright 模拟浏览器，实现小红书和抖音的扫码登录，Cookie 持久化存储到数据库，自动复用 Cookie 发布内容，Cookie 过期时前端提示重新扫码。

**Architecture:**
- 后端新增 `PlatformSession` 数据库模型存储平台 Cookie
- 每个平台新增 `login_qrcode()` 异步方法：启动 Playwright 无头浏览器 → 截取二维码图片 → 返回给前端展示
- 后端轮询检测登录状态 → 成功后提取并保存 Cookie
- 平台客户端发布时优先使用已保存的 Cookie（取代 API Key）
- 前端新增「扫码登录」Modal，显示二维码，轮询状态，成功后关闭

**Tech Stack:** Playwright (async), PostgreSQL (JSONB for cookies), FastAPI WebSocket / SSE for QR status polling, Next.js 14, React

---

## Task 1: 安装 Playwright 依赖

**Objective:** 在后端 venv 中安装 playwright，并下载 Chromium 浏览器

**Files:**
- Modify: `backend/requirements.txt`

**Steps:**

1. 在 `backend/requirements.txt` 末尾追加：
```
playwright>=1.44.0
```

2. 安装依赖并下载 Chromium：
```bash
cd ~/autonomous-ai-factory
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
```

3. 验证安装：
```bash
.venv/bin/python -c "from playwright.async_api import async_playwright; print('OK')"
```
Expected: `OK`

4. Commit:
```bash
git add backend/requirements.txt
git commit -m "feat(5d): add playwright dependency for QR login"
```

---

## Task 2: 创建 PlatformSession 数据库模型

**Objective:** 创建存储平台 Cookie 和登录状态的数据库模型

**Files:**
- Create: `backend/models/platform_session.py`
- Modify: `backend/models/__init__.py` (import新模型)
- Modify: `backend/db/init_db.py` (确保新表被创建)

**Step 1: 创建模型文件** `backend/models/platform_session.py`

```python
"""Phase 5D — Platform session / cookie storage."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class PlatformSession(UUIDMixin, TimestampMixin, Base):
    """Stores browser cookies for a platform login session."""

    __tablename__ = "platform_sessions"

    platform: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
        # "xiaohongshu" | "douyin"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
        # pending | scanning | logged_in | expired | failed
    )
    cookies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # List of cookie dicts: [{name, value, domain, path, expires, ...}]

    user_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Scraped user info after login: {nickname, user_id, avatar_url}

    qr_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Path to QR code screenshot: /static/qr/<session_id>.png

    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

**Step 2: 在 `backend/models/__init__.py` 中 import：**

在文件末尾追加：
```python
from backend.models.platform_session import PlatformSession  # noqa: F401
```

**Step 3: 确认 `backend/db/init_db.py` 已导入所有模型（通常通过 `from backend.models import *` 或逐一 import）**

查看文件内容，如果缺少 import，追加：
```python
from backend.models.platform_session import PlatformSession  # noqa: F401
```

**Step 4: 验证 py_compile：**
```bash
.venv/bin/python -m py_compile backend/models/platform_session.py && echo OK
```

**Step 5: Commit:**
```bash
git add backend/models/platform_session.py backend/models/__init__.py backend/db/init_db.py
git commit -m "feat(5d): add PlatformSession model for cookie storage"
```

---

## Task 3: 实现小红书扫码登录 Service

**Objective:** 用 Playwright 打开小红书登录页，截取二维码，保存到文件，返回图片路径

**Files:**
- Create: `backend/core/publisher/login/base.py`
- Create: `backend/core/publisher/login/xiaohongshu_login.py`

**Step 1: 创建 base 接口** `backend/core/publisher/login/base.py`

```python
"""Phase 5D — Abstract QR login interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class QRLoginSession:
    session_id: str
    platform: str
    qr_image_path: str      # /static/qr/<id>.png
    status: str             # pending | scanning | logged_in | expired | failed


@dataclass
class LoginResult:
    success: bool
    cookies: list[dict[str, Any]] | None = None
    user_info: dict[str, Any] | None = None
    error: str | None = None


class QRLoginClient(ABC):
    platform_name: str

    @abstractmethod
    async def start_login(self, session_id: str) -> QRLoginSession:
        """Launch browser, navigate to login page, screenshot QR code."""
        ...

    @abstractmethod
    async def poll_login_status(self, session_id: str) -> LoginResult:
        """Check if user has scanned the QR and logged in. Extract cookies if done."""
        ...

    @abstractmethod
    async def close(self, session_id: str) -> None:
        """Close browser for this session."""
        ...
```

**Step 2: 创建小红书登录** `backend/core/publisher/login/xiaohongshu_login.py`

```python
"""Phase 5D — Xiaohongshu QR code login via Playwright."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from backend.core.publisher.login.base import LoginResult, QRLoginClient, QRLoginSession

logger = logging.getLogger(__name__)

# In-memory store of active browser sessions: session_id -> (browser, context, page)
_active_sessions: dict[str, tuple[Any, Any, Any]] = {}


class XiaohongshuLoginClient(QRLoginClient):
    platform_name = "xiaohongshu"

    # XHS login page — QR code login tab
    LOGIN_URL = "https://www.xiaohongshu.com/explore"
    QR_SELECTOR = "img.qrcode-img"  # may need updating if XHS changes DOM
    LOGGED_IN_SELECTOR = "div.user-info, a.user-nickname, div.reds-avatar"

    async def start_login(self, session_id: str) -> QRLoginSession:
        """Launch headless Chromium, navigate to XHS, screenshot QR code."""
        # Ensure static/qr directory exists
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
            # Try to trigger QR login modal
            # Click login button if visible
            login_btn = page.locator("div.login-btn, button.sign-in, a[href*='login']")
            if await login_btn.count() > 0:
                await login_btn.first.click()
                await page.wait_for_timeout(2000)

            # Try to find QR code element
            qr_elem = page.locator(self.QR_SELECTOR)
            if await qr_elem.count() > 0:
                await qr_elem.first.screenshot(path=qr_path)
                logger.info(f"[XHS Login] QR code saved: {qr_path}")
            else:
                # Fallback: screenshot full page
                await page.screenshot(path=qr_path, full_page=False)
                logger.warning(f"[XHS Login] QR selector not found, saved full page screenshot")

        except Exception as e:
            logger.error(f"[XHS Login] start_login error: {e}")
            await browser.close()
            await pw.stop()
            del _active_sessions[session_id]
            raise

        return QRLoginSession(
            session_id=session_id,
            platform=self.platform_name,
            qr_image_path=static_path,
            status="pending",
        )

    async def poll_login_status(self, session_id: str) -> LoginResult:
        """Check if user has scanned and logged in."""
        if session_id not in _active_sessions:
            return LoginResult(success=False, error="Session not found or expired")

        _, _, context, page = _active_sessions[session_id]

        try:
            # Check if logged-in element is visible
            logged_in = page.locator(self.LOGGED_IN_SELECTOR)
            if await logged_in.count() > 0:
                # Extract cookies
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
                # Try to get user info from page
                user_info = await self._extract_user_info(page)
                return LoginResult(success=True, cookies=cookie_dicts, user_info=user_info)
            else:
                return LoginResult(success=False, error="not_yet_scanned")

        except Exception as e:
            logger.error(f"[XHS Login] poll error: {e}")
            return LoginResult(success=False, error=str(e))

    async def _extract_user_info(self, page: Page) -> dict[str, Any]:
        """Try to extract nickname/user_id from logged-in page."""
        try:
            nickname_el = page.locator("div.user-nickname, a.user-nickname").first
            nickname = await nickname_el.inner_text() if await nickname_el.count() > 0 else "unknown"
            return {"nickname": nickname.strip()}
        except Exception:
            return {}

    async def close(self, session_id: str) -> None:
        """Close browser resources for this session."""
        if session_id in _active_sessions:
            pw, browser, context, page = _active_sessions.pop(session_id)
            try:
                await browser.close()
                await pw.stop()
            except Exception as e:
                logger.warning(f"[XHS Login] close error: {e}")
```

**Step 3: 创建 `backend/core/publisher/login/__init__.py`：**
```python
from backend.core.publisher.login.xiaohongshu_login import XiaohongshuLoginClient
from backend.core.publisher.login.douyin_login import DouyinLoginClient

LOGIN_REGISTRY = {
    "xiaohongshu": XiaohongshuLoginClient,
    "douyin": DouyinLoginClient,
}

def get_login_client(platform: str):
    cls = LOGIN_REGISTRY.get(platform)
    if not cls:
        raise ValueError(f"No login client for platform: {platform}")
    return cls()
```
（注意：先只 import xiaohongshu，等 Task 4 完成后再加 douyin）

**Step 4: 验证：**
```bash
.venv/bin/python -m py_compile backend/core/publisher/login/base.py && echo OK
.venv/bin/python -m py_compile backend/core/publisher/login/xiaohongshu_login.py && echo OK
```

**Step 5: Commit:**
```bash
git add backend/core/publisher/login/
git commit -m "feat(5d): add XiaohongshuLoginClient with Playwright QR login"
```

---

## Task 4: 实现抖音扫码登录 Service

**Objective:** 用 Playwright 打开抖音创作者平台，截取二维码，检测登录成功，提取 Cookie

**Files:**
- Create: `backend/core/publisher/login/douyin_login.py`

**Step 1: 创建** `backend/core/publisher/login/douyin_login.py`

```python
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
    # QR code on douyin login modal
    QR_SELECTOR = "img.qrcode, canvas.qrcode, div.qrcode-wrap img, div[class*='qr'] img"
    LOGGED_IN_SELECTOR = "div.user-info-wrap, span.user-name, div[class*='avatar-wrap']"

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

            # Douyin redirects to login page automatically if not logged in
            qr_elem = page.locator(self.QR_SELECTOR)
            await page.wait_for_selector(
                "img.qrcode, canvas.qrcode, div[class*='qr'] img",
                timeout=10000
            )
            if await qr_elem.count() > 0:
                await qr_elem.first.screenshot(path=qr_path)
            else:
                await page.screenshot(path=qr_path)
                logger.warning("[Douyin Login] QR selector not found, saved full screenshot")

        except Exception as e:
            logger.error(f"[Douyin Login] start_login error: {e}")
            await browser.close()
            await pw.stop()
            del _active_sessions[session_id]
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
            el = page.locator("span.user-name, div[class*='user-name']").first
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
```

**Step 2: 更新 `backend/core/publisher/login/__init__.py`，加入 douyin：**

```python
from backend.core.publisher.login.xiaohongshu_login import XiaohongshuLoginClient
from backend.core.publisher.login.douyin_login import DouyinLoginClient

LOGIN_REGISTRY = {
    "xiaohongshu": XiaohongshuLoginClient,
    "douyin": DouyinLoginClient,
}

def get_login_client(platform: str):
    cls = LOGIN_REGISTRY.get(platform)
    if not cls:
        raise ValueError(f"No login client for platform: {platform}")
    return cls()
```

**Step 3: 验证：**
```bash
.venv/bin/python -m py_compile backend/core/publisher/login/douyin_login.py && echo OK
.venv/bin/python -m py_compile backend/core/publisher/login/__init__.py && echo OK
```

**Step 4: Commit:**
```bash
git add backend/core/publisher/login/
git commit -m "feat(5d): add DouyinLoginClient with Playwright QR login"
```

---

## Task 5: 创建登录 REST API

**Objective:** 提供 3 个端点：启动登录→轮询状态→登出，并将 Cookie 存储到 PlatformSession 表

**Files:**
- Create: `backend/api/platform_login.py`
- Modify: `backend/app.py` (注册新路由)

**Step 1: 创建** `backend/api/platform_login.py`

```python
"""Phase 5D — Platform QR login REST API."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.publisher.login.base import QRLoginClient
from backend.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_LOGIN_PLATFORMS = ["xiaohongshu", "douyin"]


class StartLoginResponse(BaseModel):
    session_id: str
    platform: str
    qr_image_url: str
    status: str


class LoginStatusResponse(BaseModel):
    session_id: str
    platform: str
    status: str              # pending | scanning | logged_in | expired | failed
    user_info: Optional[dict] = None
    error: Optional[str] = None


@router.post("/platform-login/start/{platform}")
async def start_qr_login(
    platform: str,
    db: AsyncSession = Depends(get_db),
) -> StartLoginResponse:
    """Start a QR login session for the given platform. Returns QR code image URL."""
    if platform not in SUPPORTED_LOGIN_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {platform}. Supported: {SUPPORTED_LOGIN_PLATFORMS}",
        )

    from backend.core.publisher.login import get_login_client
    from backend.models.platform_session import PlatformSession

    session_id = str(uuid.uuid4())
    client = get_login_client(platform)

    try:
        qr_session = await client.start_login(session_id)
    except Exception as e:
        logger.error(f"[LoginAPI] start_login failed for {platform}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start QR login: {str(e)}")

    # Persist session to DB
    db_session = PlatformSession(
        id=session_id,
        platform=platform,
        status="pending",
        qr_image_path=qr_session.qr_image_path,
    )
    db.add(db_session)
    await db.commit()

    return StartLoginResponse(
        session_id=session_id,
        platform=platform,
        qr_image_url=qr_session.qr_image_path,
        status="pending",
    )


@router.get("/platform-login/status/{session_id}")
async def poll_login_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> LoginStatusResponse:
    """Poll whether user has scanned QR and logged in."""
    from backend.core.publisher.login import get_login_client
    from backend.models.platform_session import PlatformSession

    # Load DB session
    result = await db.execute(
        select(PlatformSession).where(PlatformSession.id == session_id)
    )
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if db_session.status == "logged_in":
        return LoginStatusResponse(
            session_id=session_id,
            platform=db_session.platform,
            status="logged_in",
            user_info=db_session.user_info,
        )

    client = get_login_client(db_session.platform)
    login_result = await client.poll_login_status(session_id)

    if login_result.success:
        db_session.status = "logged_in"
        db_session.cookies = login_result.cookies
        db_session.user_info = login_result.user_info
        await db.commit()
        # Close browser session to free resources
        await client.close(session_id)
        return LoginStatusResponse(
            session_id=session_id,
            platform=db_session.platform,
            status="logged_in",
            user_info=login_result.user_info,
        )
    elif login_result.error == "not_yet_scanned":
        return LoginStatusResponse(
            session_id=session_id,
            platform=db_session.platform,
            status="pending",
        )
    else:
        db_session.status = "failed"
        db_session.error_msg = login_result.error
        await db.commit()
        await client.close(session_id)
        return LoginStatusResponse(
            session_id=session_id,
            platform=db_session.platform,
            status="failed",
            error=login_result.error,
        )


@router.get("/platform-login/sessions")
async def list_login_sessions(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all active (logged_in) platform sessions."""
    from backend.models.platform_session import PlatformSession

    result = await db.execute(
        select(PlatformSession)
        .where(PlatformSession.status == "logged_in")
        .order_by(PlatformSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "session_id": str(s.id),
            "platform": s.platform,
            "status": s.status,
            "user_info": s.user_info,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]


@router.delete("/platform-login/session/{session_id}")
async def logout_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Invalidate a platform login session (logout)."""
    from backend.core.publisher.login import get_login_client
    from backend.models.platform_session import PlatformSession

    result = await db.execute(
        select(PlatformSession).where(PlatformSession.id == session_id)
    )
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Close any active browser session
    try:
        client = get_login_client(db_session.platform)
        await client.close(session_id)
    except Exception:
        pass  # Already closed or never started

    db_session.status = "expired"
    db_session.cookies = None
    await db.commit()
    return {"status": "logged_out", "session_id": session_id}
```

**Step 2: 在 `backend/app.py` 注册路由**

找到现有路由注册处（类似 `app.include_router(publish.router)`），添加：
```python
from backend.api import platform_login
app.include_router(platform_login.router, prefix="/api", tags=["platform-login"])
```

**Step 3: 验证：**
```bash
.venv/bin/python -m py_compile backend/api/platform_login.py && echo OK
```

**Step 4: Commit:**
```bash
git add backend/api/platform_login.py backend/app.py
git commit -m "feat(5d): add platform QR login REST API"
```

---

## Task 6: 更新平台客户端，使用 Cookie 发布

**Objective:** 修改 XiaohongshuClient，发布时先从数据库获取 Cookie，用 Cookie 替代 API Key

**Files:**
- Modify: `backend/core/publisher/platforms/xiaohongshu.py`
- Modify: `backend/core/publisher/platforms/douyin.py`

**Step 1: 更新 `backend/core/publisher/platforms/xiaohongshu.py`**

在 `upload()` 方法中，在 `is_configured()` 检查**之前**，先尝试从数据库获取 Cookie：

```python
async def upload(self, bundle: dict[str, Any]) -> PlatformUploadResult:
    """Upload to XHS, using cookie-based auth if available, else API key."""
    # Try cookie-based auth first
    cookies = await self._get_session_cookies()
    if cookies:
        return await self._upload_with_cookies(bundle, cookies)

    # Fallback to API key
    if not self.is_configured():
        return PlatformUploadResult(
            platform=self.platform_name,
            success=False,
            error="credentials not configured (no cookies and no API key)",
        )
    return await self._upload_with_api_key(bundle)

async def _get_session_cookies(self) -> list[dict] | None:
    """Fetch most recent logged_in session cookies from DB."""
    try:
        from backend.db.session import AsyncSessionLocal
        from backend.models.platform_session import PlatformSession
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PlatformSession)
                .where(
                    PlatformSession.platform == self.platform_name,
                    PlatformSession.status == "logged_in",
                )
                .order_by(PlatformSession.created_at.desc())
                .limit(1)
            )
            session = result.scalar_one_or_none()
            if session and session.cookies:
                return session.cookies
    except Exception as e:
        logger.warning(f"[XHS] Failed to get session cookies: {e}")
    return None

async def _upload_with_cookies(
    self, bundle: dict[str, Any], cookies: list[dict]
) -> PlatformUploadResult:
    """Use saved browser cookies to post via httpx (simulating web client)."""
    cookie_header = "; ".join(
        f"{c['name']}={c['value']}" for c in cookies
        if c.get("domain", "").endswith("xiaohongshu.com")
    )
    headers = {
        "Cookie": cookie_header,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.xiaohongshu.com/",
    }
    # XHS creator post API (requires valid session cookie)
    api_url = "https://www.xiaohongshu.com/api/sns/v3/note"
    payload = {
        "title": bundle.get("title", "")[:20],
        "desc": bundle.get("caption", ""),
        "type": "video",
        "video_info": {
            "video_id": bundle.get("video_id", ""),
        },
        "tag_list": [
            {"id": "", "name": tag.lstrip("#")}
            for tag in bundle.get("hashtags", [])[:5]
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(api_url, json=payload, headers=headers)
            data = resp.json()
            if resp.status_code == 200 and data.get("success"):
                note_id = data.get("data", {}).get("note_id", "")
                return PlatformUploadResult(
                    platform=self.platform_name,
                    success=True,
                    post_id=note_id,
                    post_url=f"https://www.xiaohongshu.com/explore/{note_id}",
                    raw_response=data,
                )
            else:
                return PlatformUploadResult(
                    platform=self.platform_name,
                    success=False,
                    error=f"XHS API error: {data}",
                    raw_response=data,
                )
    except Exception as e:
        return PlatformUploadResult(
            platform=self.platform_name,
            success=False,
            error=str(e),
        )
```

对 `douyin.py` 做类似修改（cookie domain 改为 `douyin.com`，API URL 改为抖音）。

**Step 2: 验证：**
```bash
.venv/bin/python -m py_compile backend/core/publisher/platforms/xiaohongshu.py && echo OK
.venv/bin/python -m py_compile backend/core/publisher/platforms/douyin.py && echo OK
```

**Step 3: Commit:**
```bash
git add backend/core/publisher/platforms/xiaohongshu.py backend/core/publisher/platforms/douyin.py
git commit -m "feat(5d): platform clients use cookie-based auth when session available"
```

---

## Task 7: 前端 — 扫码登录 Modal 组件

**Objective:** 创建扫码登录 Modal，展示二维码图片，每 3 秒轮询状态，登录成功后关闭并刷新状态

**Files:**
- Create: `frontend/components/qr-login-modal.tsx`
- Modify: `frontend/components/publish-panel.tsx` (添加「扫码登录」按钮)

**Step 1: 创建** `frontend/components/qr-login-modal.tsx`

```tsx
"use client";

import { useState, useEffect, useCallback } from "react";

interface QRLoginModalProps {
  platform: "xiaohongshu" | "douyin";
  onClose: () => void;
  onSuccess: (platform: string, userInfo: Record<string, unknown>) => void;
}

interface LoginStatus {
  session_id: string;
  platform: string;
  status: "pending" | "scanning" | "logged_in" | "expired" | "failed";
  user_info?: Record<string, unknown>;
  error?: string;
}

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
};

export default function QRLoginModal({ platform, onClose, onSuccess }: QRLoginModalProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<LoginStatus["status"]>("pending");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const platformLabel = PLATFORM_LABELS[platform] || platform;

  // Start login session
  useEffect(() => {
    const startLogin = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/platform-login/start/${platform}`, {
          method: "POST",
        });
        if (!res.ok) throw new Error("Failed to start login");
        const data = await res.json();
        setSessionId(data.session_id);
        setQrImageUrl(data.qr_image_url);
        setLoading(false);
      } catch (e) {
        setError("无法启动登录，请稍后重试");
        setLoading(false);
      }
    };
    startLogin();
  }, [platform]);

  // Poll status every 3 seconds
  useEffect(() => {
    if (!sessionId || status === "logged_in" || status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/platform-login/status/${sessionId}`);
        const data: LoginStatus = await res.json();
        setStatus(data.status);
        if (data.status === "logged_in") {
          clearInterval(interval);
          onSuccess(platform, data.user_info || {});
        } else if (data.status === "failed") {
          clearInterval(interval);
          setError(data.error || "登录失败");
        }
      } catch (e) {
        console.error("Poll error:", e);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [sessionId, status, platform, onSuccess]);

  const handleCancel = useCallback(async () => {
    if (sessionId) {
      // Clean up session
      await fetch(`/api/platform-login/session/${sessionId}`, { method: "DELETE" });
    }
    onClose();
  }, [sessionId, onClose]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 w-96 text-center shadow-xl">
        <h2 className="text-xl font-bold mb-2">
          {platformLabel} 扫码登录
        </h2>
        <p className="text-gray-500 text-sm mb-6">
          打开 {platformLabel} App，扫描下方二维码
        </p>

        {loading && (
          <div className="h-48 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500" />
          </div>
        )}

        {!loading && qrImageUrl && status !== "logged_in" && (
          <div className="relative inline-block mb-4">
            <img
              src={`/api${qrImageUrl}`}
              alt="QR Code"
              className="w-48 h-48 mx-auto border rounded-lg"
            />
            {status === "scanning" && (
              <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-lg">
                <span className="text-green-600 font-semibold">扫描成功，请确认...</span>
              </div>
            )}
          </div>
        )}

        {status === "logged_in" && (
          <div className="h-48 flex flex-col items-center justify-center gap-3">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-green-600 font-semibold">登录成功！</p>
          </div>
        )}

        {error && (
          <p className="text-red-500 text-sm mb-4">{error}</p>
        )}

        <div className="flex gap-3 mt-4">
          <button
            onClick={handleCancel}
            className="flex-1 py-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition"
          >
            {status === "logged_in" ? "关闭" : "取消"}
          </button>
          {status !== "logged_in" && (
            <button
              onClick={() => {
                setLoading(true);
                setError(null);
                setSessionId(null);
                setQrImageUrl(null);
                setStatus("pending");
                // Re-trigger useEffect by incrementing key (handled by parent)
              }}
              className="flex-1 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition"
            >
              刷新二维码
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 2: 在 `frontend/components/publish-panel.tsx` 添加「扫码登录」按钮**

在 publish panel 顶部添加「平台登录状态」区域：
```tsx
// 在组件 state 中添加：
const [showQRLogin, setShowQRLogin] = useState<"xiaohongshu" | "douyin" | null>(null);
const [loginSessions, setLoginSessions] = useState<Record<string, boolean>>({});

// 登录成功回调
const handleLoginSuccess = (platform: string) => {
  setLoginSessions(prev => ({ ...prev, [platform]: true }));
  setShowQRLogin(null);
};

// 在 JSX 顶部添加登录状态栏：
<div className="flex gap-3 mb-4">
  {["xiaohongshu", "douyin"].map(p => (
    <button
      key={p}
      onClick={() => setShowQRLogin(p as "xiaohongshu" | "douyin")}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
        loginSessions[p]
          ? "bg-green-100 text-green-700 border border-green-300"
          : "bg-gray-100 text-gray-600 border border-gray-300 hover:bg-gray-200"
      }`}
    >
      {loginSessions[p] ? "✅" : "🔐"}{" "}
      {p === "xiaohongshu" ? "小红书" : "抖音"}
      {loginSessions[p] ? " 已登录" : " 扫码登录"}
    </button>
  ))}
</div>

// QR Login Modal
{showQRLogin && (
  <QRLoginModal
    platform={showQRLogin}
    onClose={() => setShowQRLogin(null)}
    onSuccess={handleLoginSuccess}
  />
)}
```

**Step 3: 验证 TypeScript 语法（不运行编译）：**
目视检查 JSX 无明显语法错误即可。

**Step 4: Commit:**
```bash
git add frontend/components/qr-login-modal.tsx frontend/components/publish-panel.tsx
git commit -m "feat(5d): add QR login modal with polling and status display"
```

---

## Task 8: 静态文件服务配置

**Objective:** 确保 FastAPI 能静态服务 `/static/qr/` 目录下的二维码图片

**Files:**
- Modify: `backend/app.py`

**Step 1: 在 `backend/app.py` 中确认 `StaticFiles` 挂载包含 qr 目录：**

```python
import os
from fastapi.staticfiles import StaticFiles

# 确保 static 目录存在
os.makedirs("static/qr", exist_ok=True)

# 挂载（如果已有 static 挂载，无需重复，qr 子目录自动包含）
app.mount("/static", StaticFiles(directory="static"), name="static")
```

**Step 2: 验证：**
```bash
mkdir -p ~/autonomous-ai-factory/static/qr
ls ~/autonomous-ai-factory/static/
```
Expected: `qr/` 目录出现

**Step 3: Commit:**
```bash
git add backend/app.py
git commit -m "feat(5d): serve /static/qr/ for QR code images"
```

---

## Task 9: 最终验证 + 文档更新

**Objective:** py_compile 所有新文件，更新 .env.example 说明，提交

**Steps:**

1. 验证所有新 Python 文件：
```bash
cd ~/autonomous-ai-factory
for f in backend/core/publisher/login/*.py backend/api/platform_login.py backend/models/platform_session.py; do
  .venv/bin/python -m py_compile "$f" && echo "OK: $f"
done
```
Expected: 每行输出 `OK: <file>`

2. 更新 `.env.example`，追加注释（不需要 env vars，因为 cookie-based）：
```
# ── Phase 5D: QR Login (no API keys needed) ──────────────────────
# Login sessions are stored in PostgreSQL platform_sessions table.
# Use the /api/platform-login/start/{platform} endpoint to initiate QR login.
# PLAYWRIGHT_HEADLESS=true  # default is true; set false for debugging
```

3. Commit 全部：
```bash
git add .
git commit -m "feat(5d): complete QR login implementation — xiaohongshu + douyin"
```

---

## 完成标志

- [ ] `playwright` 安装完成，Chromium 可下载
- [ ] `PlatformSession` 表存在（`init_db.py` 运行后）
- [ ] `POST /api/platform-login/start/xiaohongshu` 返回 `qr_image_url`
- [ ] `GET /api/platform-login/status/{session_id}` 轮询可用
- [ ] 前端 Publish Panel 出现「🔐 小红书 扫码登录」按钮，点击弹出二维码 Modal
- [ ] 扫码成功后状态变为「✅ 小红书 已登录」
- [ ] 发布时平台客户端优先使用 Cookie

## 已知限制

- 二维码 **2分钟** 内有效，超时需刷新
- Playwright 无头浏览器占用约 **200MB 内存**（每个 session）
- XHS/抖音可能更新 DOM 选择器，届时需要更新 `QR_SELECTOR` 和 `LOGGED_IN_SELECTOR`
- Cookie 有效期一般为 **30天**，过期后前端会显示「请重新扫码」提示
