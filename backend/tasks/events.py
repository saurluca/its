from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Set
from uuid import UUID

from fastapi import WebSocket


TaskGenerationStatus = dict[str, Any]


class TaskGenerationEventManager:
    """Manage WebSocket connections and status broadcasts for task generation."""

    def __init__(self) -> None:
        self._connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        self._latest_status: Dict[UUID, TaskGenerationStatus] = {}
        self._lock = asyncio.Lock()

    async def connect(self, unit_id: UUID, websocket: WebSocket) -> None:
        """Register a websocket for a unit and replay the last known status."""

        await websocket.accept()

        async with self._lock:
            self._connections[unit_id].add(websocket)
            latest_status = self._latest_status.get(unit_id)

        if latest_status:
            await self._safe_send(websocket, latest_status)

    async def disconnect(self, unit_id: UUID, websocket: WebSocket) -> None:
        """Remove a websocket for a unit."""

        async with self._lock:
            connections = self._connections.get(unit_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(unit_id, None)

    async def broadcast_status(
        self,
        unit_id: UUID,
        status: str,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast status update to all connected clients for a unit.

        Args:
            unit_id: The unit ID for which tasks are being generated
            status: One of 'processing', 'success', 'error'
            message: Optional message to display to user
            payload: Optional additional data (e.g., error details, task count)
        """

        event: TaskGenerationStatus = {
            "type": "task_generation",
            "unit_id": str(unit_id),
            "status": status,
            "message": message,
            "payload": payload or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            self._latest_status[unit_id] = event
            connections = list(self._connections.get(unit_id, set()))

        if not connections:
            return

        stale_connections: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(event)
            except Exception:
                stale_connections.append(websocket)

        if stale_connections:
            async with self._lock:
                active_connections = self._connections.get(unit_id)
                if not active_connections:
                    return
                for websocket in stale_connections:
                    active_connections.discard(websocket)
                if not active_connections:
                    self._connections.pop(unit_id, None)

    async def _safe_send(
        self, websocket: WebSocket, event: TaskGenerationStatus
    ) -> None:
        try:
            await websocket.send_json(event)
        except Exception:
            # Ignore send failures during replay; caller handles connection cleanup.
            pass


task_generation_events_manager = TaskGenerationEventManager()
