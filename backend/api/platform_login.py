"""Phase 5D — Platform QR login REST API."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    status: str
    user_info: Optional[dict] = None
    error: Optional[str] = None


@router.post("/platform-login/start/{platform}")
async def start_qr_login(
    platform: str,
    db: AsyncSession = Depends(get_db),
) -> StartLoginResponse:
    """Start a QR login session. Returns QR image URL."""
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
) -> dict:
    """Invalidate a platform login session (logout)."""
    from backend.core.publisher.login import get_login_client
    from backend.models.platform_session import PlatformSession

    result = await db.execute(
        select(PlatformSession).where(PlatformSession.id == session_id)
    )
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        client = get_login_client(db_session.platform)
        await client.close(session_id)
    except Exception:
        pass

    db_session.status = "expired"
    db_session.cookies = None
    await db.commit()
    return {"status": "logged_out", "session_id": session_id}
