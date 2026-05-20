"""backend/core/publisher/login/base.py — Stub base classes for QR-code login clients.

NOTE: This file was auto-generated as a stub. The authoritative version
      may be replaced by another task in the pipeline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QRLoginSession:
    """Holds the data returned when a QR login flow is initiated."""

    session_id: str
    platform: str
    qr_image_path: str          # URL / static path the frontend can display
    status: str = "pending"     # pending | scanned | success | expired


@dataclass
class LoginResult:
    """Returned by poll_login_status() once the user has (or hasn't) scanned."""

    success: bool
    cookies: list[dict[str, Any]] = field(default_factory=list)
    user_info: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class QRLoginClient(ABC):
    """Abstract base for all QR-code-based platform login clients."""

    platform_name: str

    @abstractmethod
    async def start_login(self, session_id: str) -> QRLoginSession:
        """Launch a headless browser, navigate to the login page, capture the
        QR code image, and return a :class:`QRLoginSession`."""
        ...

    @abstractmethod
    async def poll_login_status(self, session_id: str) -> LoginResult:
        """Check whether the user has scanned the QR code and return the
        result (cookies + user info on success)."""
        ...

    @abstractmethod
    async def close(self, session_id: str) -> None:
        """Tear down the browser / playwright context for *session_id*."""
        ...
