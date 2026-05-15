"""
WebSocket API for real-time updates.
"""
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from backend.db.session import AsyncSessionLocal
from backend.models.project import Project

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for projects."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, project_id: str, websocket: WebSocket) -> None:
        """
        Accept and register a WebSocket connection.

        Args:
            project_id: Project UUID
            websocket: WebSocket connection
        """
        await websocket.accept()

        if project_id not in self.active_connections:
            self.active_connections[project_id] = []

        self.active_connections[project_id].append(websocket)

    def disconnect(self, project_id: str, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Args:
            project_id: Project UUID
            websocket: WebSocket connection
        """
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)

            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def send_message(
        self,
        project_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Send message to all connections for a project.

        Args:
            project_id: Project UUID
            message: Message data
        """
        if project_id not in self.active_connections:
            return

        message_json = json.dumps(message)

        # Send to all connections
        for connection in self.active_connections[project_id]:
            try:
                await connection.send_text(message_json)
            except Exception:
                # Connection may have closed
                pass

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Broadcast message to all connections.

        Args:
            message: Message data
        """
        message_json = json.dumps(message)

        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(project_id: str, websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time project updates.

    Sends events:
    - {type: 'project_status', status: string}
    - {type: 'task_update', task_id: string, status: string, message: string}
    - {type: 'agent_log', agent_name: string, message: string, level: string}
    - {type: 'test_result', test_type: string, passed: bool, error: string}
    - {type: 'deployment_update', environment: string, url: string, status: string}
    - {type: 'pipeline_complete', report_url: string}

    Args:
        project_id: Project UUID
        websocket: WebSocket connection
    """
    await manager.connect(project_id, websocket)

    try:
        # Send initial project status
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if project:
                await websocket.send_json({
                    "type": "project_status",
                    "status": project.status.value,
                })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back for now (can be extended for client commands)
                await websocket.send_json({
                    "type": "echo",
                    "message": data,
                })
            except WebSocketDisconnect:
                break

    except Exception as e:
        print(f"WebSocket error for project {project_id}: {str(e)}")

    finally:
        manager.disconnect(project_id, websocket)


# Helper functions for sending events (to be used by orchestrator/workers)
async def send_project_status(project_id: str, status: str) -> None:
    """Send project status update."""
    await manager.send_message(
        project_id,
        {"type": "project_status", "status": status},
    )


async def send_task_update(
    project_id: str,
    task_id: str,
    status: str,
    message: str,
) -> None:
    """Send task update."""
    await manager.send_message(
        project_id,
        {
            "type": "task_update",
            "task_id": task_id,
            "status": status,
            "message": message,
        },
    )


async def send_agent_log(
    project_id: str,
    agent_name: str,
    message: str,
    level: str = "info",
) -> None:
    """Send agent log."""
    await manager.send_message(
        project_id,
        {
            "type": "agent_log",
            "agent_name": agent_name,
            "message": message,
            "level": level,
        },
    )


async def send_test_result(
    project_id: str,
    test_type: str,
    passed: bool,
    error: str = "",
) -> None:
    """Send test result."""
    await manager.send_message(
        project_id,
        {
            "type": "test_result",
            "test_type": test_type,
            "passed": passed,
            "error": error,
        },
    )


async def send_deployment_update(
    project_id: str,
    environment: str,
    url: str,
    status: str,
) -> None:
    """Send deployment update."""
    await manager.send_message(
        project_id,
        {
            "type": "deployment_update",
            "environment": environment,
            "url": url,
            "status": status,
        },
    )


async def send_pipeline_complete(project_id: str, report_url: str) -> None:
    """Send pipeline completion notification."""
    await manager.send_message(
        project_id,
        {
            "type": "pipeline_complete",
            "report_url": report_url,
        },
    )
