"""
Dashboard router — system statistics, logs, and overview APIs.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.websocket_manager import ws_manager
from app.models.user import User
from app.services import incident_service, drone_service, alert_service, log_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/overview",
    summary="System overview stats",
)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a comprehensive overview of the system state:
    - Incident statistics
    - Drone fleet summary
    - Unread alerts count
    - WebSocket connection counts
    - Log statistics
    """
    incident_stats = await incident_service.get_incident_stats(db)
    drone_list = await drone_service.list_drones(db)
    unread_alerts = await alert_service.get_unread_count(db)
    log_stats = await log_service.get_log_stats(db)
    ws_connections = ws_manager.get_all_channel_counts()

    # Compute fleet summary
    fleet = {
        "total_drones": drone_list.total,
        "by_status": {},
    }
    for drone in drone_list.drones:
        status = drone.status
        fleet["by_status"][status] = fleet["by_status"].get(status, 0) + 1

    return {
        "incidents": incident_stats,
        "fleet": fleet,
        "unread_alerts": unread_alerts,
        "websocket_connections": ws_connections,
        "logs": log_stats,
    }


@router.get(
    "/incident-timeline",
    summary="Incident timeline",
)
async def incident_timeline(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a chronological timeline of recent incidents."""
    incidents = await incident_service.get_incident_timeline(db, limit)
    return {"timeline": [i.model_dump(mode="json") for i in incidents]}


@router.get(
    "/logs",
    summary="System logs",
)
async def get_logs(
    level: Optional[str] = None,
    module: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query system logs with optional level and module filters."""
    logs = await log_service.get_logs(db, level, module, skip, limit)
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "level": log.level.value,
                "module": log.module,
                "action": log.action,
                "message": log.message,
                "metadata": log.metadata,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
