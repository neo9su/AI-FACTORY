"""Auth API routes: register, login, profile, user list.

Endpoints:
  POST /api/v1/auth/register — create user
  POST /api/v1/auth/login    — get access+refresh tokens
  GET  /api/v1/auth/profile   — current user info (JWT required)
  GET  /api/v1/auth/users     — list users (admin only)
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.models import (
    User,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.models.auth import UserStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Request/Response schemas ───────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None
    role: str
    status: str
    avatar_url: str | None
    last_login_at: str | None
    is_email_verified: bool

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None

# ─── Current user dependency ────────────────────────────────────────────────

async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT and return the current user."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    result = await db.execute(select(User).where(User.username == sub))
    user = result.scalar_one_or_none()
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.email == req.email) | (User.username == req.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Username or email already taken")

    user = User(
        email=req.email,
        username=req.username,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"[Auth] User registered: {user.username}")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with username/password, return access + refresh tokens."""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid username or password")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(403, "Account is not active")

    # Update last login
    from datetime import datetime, timezone
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Generate tokens
    access_token = create_access_token({"sub": user.username, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.username, "role": user.role.value})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/profile", response_model=UserOut)
async def get_profile(user: Annotated[User, Depends(get_current_user)]):
    """Get current user profile."""
    return user


@router.get("/users")
async def list_users(user: Annotated[User, Depends(get_current_user)]):
    """List all users (admin only)."""
    if user.role.value != "admin":
        raise HTTPException(403, "Admin only")
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [u.model_dump() for u in users]
