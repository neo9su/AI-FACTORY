"""
Webhook notification system for the AI Factory.

Sends HTTP POST notifications to configured URLs when pipeline events occur.
Supports delivery confirmation, failure alerts, and stage transitions.

Configuration via environment variables:
- WEBHOOK_URL: Primary webhook endpoint (receives all events)
- WEBHOOK_SECRET: Optional HMAC secret for payload signing
- WEBHOOK_EVENTS: Comma-separated list of events to send (default: all)
  Valid events: pipeline.started, pipeline.completed, pipeline.failed,
               stage.changed, test.completed, review.completed

Payload format:
{
  "event": "pipeline.completed",
  "project_id": "uuid",
  "project_name": "My Project",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": { ... event-specific data ... }
}
"""
import asyncio
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional


class WebhookNotifier:
    """Sends webhook notifications for pipeline events."""

    def __init__(self) -> None:
        self.url = os.getenv("WEBHOOK_URL", "")
        self.secret = os.getenv("WEBHOOK_SECRET", "")
        self.enabled_events = self._parse_events(os.getenv("WEBHOOK_EVENTS", ""))

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def _parse_events(self, events_str: str) -> set[str]:
        """Parse comma-separated event list. Empty = all events."""
        if not events_str.strip():
            return set()  # Empty means all events are enabled
        return {e.strip() for e in events_str.split(",") if e.strip()}

    def _should_send(self, event: str) -> bool:
        """Check if this event should be sent."""
        if not self.enabled:
            return False
        if not self.enabled_events:
            return True  # Empty set = all events
        return event in self.enabled_events

    def _sign_payload(self, payload: bytes) -> str:
        """Generate HMAC-SHA256 signature for payload."""
        if not self.secret:
            return ""
        return hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

    async def send(
        self,
        event: str,
        project_id: str,
        project_name: str,
        data: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Send a webhook notification.

        Args:
            event: Event type (e.g., "pipeline.completed")
            project_id: Project UUID
            project_name: Human-readable project name
            data: Additional event-specific data

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self._should_send(event):
            return False

        payload = {
            "event": event,
            "project_id": project_id,
            "project_name": project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }

        payload_bytes = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Factory-Webhook/1.0",
            "X-Webhook-Event": event,
        }

        if self.secret:
            signature = hmac.new(
                self.secret.encode(),
                payload_bytes,
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        try:
            cmd = self._build_curl_command(headers, payload_bytes)
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=10)
            return process.returncode == 0
        except Exception:
            return False

    def _build_curl_command(self, headers: dict[str, str], payload: bytes) -> str:
        """Build curl command for sending webhook."""
        header_args = " ".join(f'-H "{k}: {v}"' for k, v in headers.items())
        # Escape single quotes in payload
        escaped = payload.decode("utf-8").replace("'", "'\\''")
        return f"curl -s -o /dev/null -w '%{{http_code}}' -X POST {header_args} -d '{escaped}' '{self.url}'"

    # ─── Convenience methods ─────────────────────────────────────────────

    async def notify_pipeline_started(self, project_id: str, project_name: str) -> bool:
        return await self.send("pipeline.started", project_id, project_name)

    async def notify_pipeline_completed(
        self,
        project_id: str,
        project_name: str,
        duration_seconds: float,
        repo_url: Optional[str] = None,
    ) -> bool:
        return await self.send(
            "pipeline.completed",
            project_id,
            project_name,
            data={
                "duration_seconds": round(duration_seconds, 1),
                "repo_url": repo_url,
            },
        )

    async def notify_pipeline_failed(
        self,
        project_id: str,
        project_name: str,
        error: str,
        stage: str = "",
    ) -> bool:
        return await self.send(
            "pipeline.failed",
            project_id,
            project_name,
            data={"error": error[:500], "stage": stage},
        )

    async def notify_stage_changed(
        self,
        project_id: str,
        project_name: str,
        stage: str,
    ) -> bool:
        return await self.send(
            "stage.changed",
            project_id,
            project_name,
            data={"stage": stage},
        )

    async def notify_review_completed(
        self,
        project_id: str,
        project_name: str,
        score: int,
        issues_count: int,
    ) -> bool:
        return await self.send(
            "review.completed",
            project_id,
            project_name,
            data={"score": score, "issues_count": issues_count},
        )


# Module-level singleton
_webhook_notifier: Optional[WebhookNotifier] = None


def get_webhook_notifier() -> WebhookNotifier:
    """Get or create the webhook notifier singleton."""
    global _webhook_notifier
    if _webhook_notifier is None:
        _webhook_notifier = WebhookNotifier()
    return _webhook_notifier
