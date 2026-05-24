"""
Webhook notification system for the AI Factory.

Sends HTTP POST notifications to a configured webhook URL on key pipeline events:
- pipeline.started — when a project pipeline begins
- pipeline.completed — when a project is delivered successfully
- pipeline.failed — when a project pipeline fails
- review.completed — when code review finishes

The webhook payload includes project details, status, and event metadata.
Failures are logged but never block the pipeline.

Configuration (env vars or settings API):
- WEBHOOK_URL: Target URL for POST requests
- WEBHOOK_EVENTS: Comma-separated events to send (empty = all)
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Any, Optional


class WebhookNotifier:
    """Sends webhook notifications for pipeline events."""

    def __init__(self) -> None:
        self.url = os.getenv("WEBHOOK_URL", "")
        self.events = self._parse_events(os.getenv("WEBHOOK_EVENTS", ""))
        self.timeout = 10  # seconds

    def _parse_events(self, events_str: str) -> set[str]:
        """Parse comma-separated events filter. Empty = all events."""
        if not events_str.strip():
            return set()  # Empty = send all events
        return {e.strip().lower() for e in events_str.split(",") if e.strip()}

    def _should_send(self, event_type: str) -> bool:
        """Check if this event should be sent based on filter."""
        if not self.url:
            return False
        if not self.events:
            return True  # No filter = send all
        return event_type.lower() in self.events

    async def send(
        self,
        event_type: str,
        project_id: str,
        project_name: str,
        data: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Send a webhook notification.

        Args:
            event_type: Event name (e.g., "pipeline.completed")
            project_id: Project UUID
            project_name: Human-readable project name
            data: Additional event-specific data

        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Reload URL from env (in case settings changed at runtime)
        self.url = os.getenv("WEBHOOK_URL", "")
        self.events = self._parse_events(os.getenv("WEBHOOK_EVENTS", ""))

        if not self._should_send(event_type):
            return False

        payload = json.dumps({
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "project": {
                "id": project_id,
                "name": project_name,
            },
            "data": data or {},
        })

        try:
            cmd = (
                f'curl -s -o /dev/null -w "%{{http_code}}" '
                f'-X POST "{self.url}" '
                f'-H "Content-Type: application/json" '
                f'-H "X-Webhook-Event: {event_type}" '
                f'-H "User-Agent: AI-Factory-Webhook/1.0" '
                f"--max-time {self.timeout} "
                f"-d '{payload}'"
            )

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=self.timeout + 5)
            status_code = stdout.decode().strip()

            return status_code.startswith("2")  # 2xx = success

        except Exception:
            return False

    async def pipeline_started(self, project_id: str, project_name: str) -> None:
        """Notify that a pipeline has started."""
        await self.send("pipeline.started", project_id, project_name)

    async def pipeline_completed(
        self,
        project_id: str,
        project_name: str,
        duration_seconds: float = 0,
        repo_url: str = "",
        preview_url: str = "",
    ) -> None:
        """Notify that a pipeline has completed successfully."""
        await self.send(
            "pipeline.completed",
            project_id,
            project_name,
            data={
                "duration_seconds": round(duration_seconds, 1),
                "repo_url": repo_url,
                "preview_url": preview_url,
            },
        )

    async def pipeline_failed(
        self,
        project_id: str,
        project_name: str,
        error: str = "",
        stage: str = "",
    ) -> None:
        """Notify that a pipeline has failed."""
        await self.send(
            "pipeline.failed",
            project_id,
            project_name,
            data={
                "error": error[:500],
                "failed_at_stage": stage,
            },
        )

    async def review_completed(
        self,
        project_id: str,
        project_name: str,
        score: int = 0,
        passed: bool = True,
        issues_count: int = 0,
    ) -> None:
        """Notify that code review has completed."""
        await self.send(
            "review.completed",
            project_id,
            project_name,
            data={
                "score": score,
                "passed": passed,
                "issues_count": issues_count,
            },
        )


# Module-level singleton
_webhook_notifier: Optional[WebhookNotifier] = None


def get_webhook_notifier() -> WebhookNotifier:
    """Get or create the webhook notifier singleton."""
    global _webhook_notifier
    if _webhook_notifier is None:
        _webhook_notifier = WebhookNotifier()
    return _webhook_notifier
