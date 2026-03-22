"""
WebSocket router — real-time communication channels.

Channels:
  - /ws/drones    → Live drone telemetry updates
  - /ws/incidents → Incident creation and updates
  - /ws/alerts    → Alert notifications
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.websocket_manager import ws_manager

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/drones")
async def ws_drones(websocket: WebSocket):
    """
    WebSocket endpoint for live drone tracking.

    Clients connecting here receive:
    - telemetry_update: Real-time position and battery updates.
    - drone_dispatched: Notification when a drone is dispatched.
    """
    await ws_manager.connect(websocket, channel="drones")
    try:
        while True:
            # Keep connection alive; clients can also send messages
            data = await websocket.receive_json()
            # Echo back for testing / acknowledgement
            await ws_manager.send_personal(
                websocket,
                {"event": "ack", "data": data},
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel="drones")
        logger.info("WS client disconnected from 'drones' channel")
    except Exception as e:
        ws_manager.disconnect(websocket, channel="drones")
        logger.warning("WS error on 'drones' channel: {}", e)


@router.websocket("/ws/incidents")
async def ws_incidents(websocket: WebSocket):
    """
    WebSocket endpoint for incident updates.

    Clients connecting here receive:
    - new_incident:     Notification when an incident is created.
    - incident_updated: Notification when an incident status changes.
    - drone_dispatched: Notification when a drone is dispatched to an incident.
    """
    await ws_manager.connect(websocket, channel="incidents")
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.send_personal(
                websocket,
                {"event": "ack", "data": data},
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel="incidents")
        logger.info("WS client disconnected from 'incidents' channel")
    except Exception as e:
        ws_manager.disconnect(websocket, channel="incidents")
        logger.warning("WS error on 'incidents' channel: {}", e)


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for alert notifications.

    Clients connecting here receive:
    - new_alert: Notification when a new alert is generated.
    """
    await ws_manager.connect(websocket, channel="alerts")
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.send_personal(
                websocket,
                {"event": "ack", "data": data},
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel="alerts")
        logger.info("WS client disconnected from 'alerts' channel")
    except Exception as e:
        ws_manager.disconnect(websocket, channel="alerts")
        logger.warning("WS error on 'alerts' channel: {}", e)


@router.websocket("/ws/all")
async def ws_all(websocket: WebSocket):
    """
    Unified WebSocket endpoint — receives ALL events from all channels.
    Useful for dashboard clients that need a single connection.
    """
    await ws_manager.connect(websocket, channel="drones")
    await ws_manager.connect(websocket, channel="incidents")
    await ws_manager.connect(websocket, channel="alerts")
    try:
        while True:
            data = await websocket.receive_json()
            await ws_manager.send_personal(
                websocket,
                {"event": "ack", "channel": "all", "data": data},
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel="drones")
        ws_manager.disconnect(websocket, channel="incidents")
        ws_manager.disconnect(websocket, channel="alerts")
        logger.info("WS client disconnected from 'all' channel")
    except Exception as e:
        ws_manager.disconnect(websocket, channel="drones")
        ws_manager.disconnect(websocket, channel="incidents")
        ws_manager.disconnect(websocket, channel="alerts")
        logger.warning("WS error on 'all' channel: {}", e)
