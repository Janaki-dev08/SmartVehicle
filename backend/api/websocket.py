"""
WebSocket Manager for High-Frequency Real-Time Telemetry Streaming.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio


class ConnectionManager:
    """
    Manages active WebSocket client connections and broadcasts simulation telemetry.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Client connected (Total active: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WebSocket] Client disconnected (Remaining: {len(self.active_connections)})")

    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcasts structured telemetry frame to all connected frontend clients."""
        if not self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()
