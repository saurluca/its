from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Set
from uuid import UUID

from fastapi import WebSocket


DocumentStatus = dict[str, Any]


class DocumentProcessingEventManager:
    """Manage WebSocket connections and status broadcasts for document processing."""

    def __init__(self) -> None:
        self._connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        self._latest_status: Dict[UUID, DocumentStatus] = {}
        self._lock = asyncio.Lock()

    async def connect(self, document_id: UUID, websocket: WebSocket) -> None:
        """Register a websocket for a document and replay the last known status."""

        await websocket.accept()

        async with self._lock:
            self._connections[document_id].add(websocket)
            latest_status = self._latest_status.get(document_id)

        if latest_status:
            await self._safe_send(websocket, latest_status)

    async def disconnect(self, document_id: UUID, websocket: WebSocket) -> None:
        """Remove a websocket for a document."""

        async with self._lock:
            connections = self._connections.get(document_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(document_id, None)

    async def broadcast_status(
        self,
        document_id: UUID,
        status: str,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a status update to all listeners for the document."""

        event: DocumentStatus = {
            "type": "document_processing",
            "document_id": str(document_id),
            "status": status,
            "message": message,
            "payload": payload or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            self._latest_status[document_id] = event
            connections = list(self._connections.get(document_id, set()))

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
                active_connections = self._connections.get(document_id)
                if not active_connections:
                    return
                for websocket in stale_connections:
                    active_connections.discard(websocket)
                if not active_connections:
                    self._connections.pop(document_id, None)

    async def _safe_send(self, websocket: WebSocket, event: DocumentStatus) -> None:
        try:
            await websocket.send_json(event)
        except Exception:
            # Ignore send failures during replay; caller handles connection cleanup.
            pass


document_events_manager = DocumentProcessingEventManager()
