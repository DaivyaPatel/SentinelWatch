"""
WebSocket connection manager.
Supports multiple named channels (drones, incidents, alerts) so that
clients can subscribe to specific real-time feeds.
"""

from typing import Dict, List
from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """
    Manages WebSocket connections across named channels.

    Usage:
        manager = ConnectionManager()
        await manager.connect(websocket, channel="drones")
        await manager.broadcast({"drone_id": 1, ...}, channel="drones")
    """

    def __init__(self) -> None:
        # channel_name → list of active WebSocket connections
        self._channels: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default") -> None:
        """Accept a WebSocket and register it under the given channel."""
        await websocket.accept()
        self._channels.setdefault(channel, []).append(websocket)
        logger.info("WS connected — channel='{}', total={}", channel, len(self._channels[channel]))

    def disconnect(self, websocket: WebSocket, channel: str = "default") -> None:
        """Remove a WebSocket from the channel."""
        if channel in self._channels:
            self._channels[channel] = [
                ws for ws in self._channels[channel] if ws is not websocket
            ]
            logger.info("WS disconnected — channel='{}', remaining={}", channel, len(self._channels[channel]))

    async def send_personal(self, websocket: WebSocket, data: dict) -> None:
        """Send a JSON message to a single client."""
        try:
            await websocket.send_json(data)
        except Exception as exc:
            logger.warning("Failed to send personal WS message: {}", exc)

    async def broadcast(self, data: dict, channel: str = "default") -> None:
        """Broadcast a JSON message to all clients in a channel."""
        dead_connections: List[WebSocket] = []
        for ws in self._channels.get(channel, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead_connections.append(ws)

        # Prune dead connections
        for ws in dead_connections:
            self.disconnect(ws, channel)

    def get_connection_count(self, channel: str = "default") -> int:
        """Return the number of active connections in a channel."""
        return len(self._channels.get(channel, []))

    def get_all_channel_counts(self) -> Dict[str, int]:
        """Return connection counts for every channel."""
        return {ch: len(conns) for ch, conns in self._channels.items()}


# ---------------------------------------------------------------------------
# Singleton instance used across the application
# ---------------------------------------------------------------------------
ws_manager = ConnectionManager()
