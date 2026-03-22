"""
Drone management router — CRUD, telemetry, and fleet operations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.core.websocket_manager import ws_manager
from app.models.user import User
from app.schemas.drone import (
    DroneCreate, DroneUpdate, DroneTelemetry,
    DroneResponse, DroneListResponse,
)
from app.services import drone_service

router = APIRouter(prefix="/drones", tags=["Drone Management"])


@router.post(
    "",
    response_model=DroneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new drone",
    responses={
        201: {
            "description": "Drone registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Drone-Alpha-01",
                        "model": "DJI-Matrice-300",
                        "battery_level": 95.0,
                        "latitude": 28.6139,
                        "longitude": 77.2090,
                        "altitude": 0.0,
                        "speed": 0.0,
                        "status": "idle",
                        "is_active": True,
                        "last_heartbeat": "2026-03-21T16:30:00Z",
                        "created_at": "2026-03-21T16:30:00Z",
                        "updated_at": "2026-03-21T16:30:00Z",
                    }
                }
            },
        },
    },
)
async def create_drone(
    data: DroneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new drone in the fleet."""
    try:
        return await drone_service.create_drone(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=DroneListResponse,
    summary="List all drones",
)
async def list_drones(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List drones with optional status filter and pagination."""
    return await drone_service.list_drones(db, status_filter, skip, limit)


@router.get(
    "/{drone_id}",
    response_model=DroneResponse,
    summary="Get drone details",
)
async def get_drone(
    drone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a single drone by ID."""
    try:
        return await drone_service.get_drone_by_id(db, drone_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{drone_id}",
    response_model=DroneResponse,
    summary="Update drone details",
)
async def update_drone(
    drone_id: int,
    data: DroneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partially update a drone record."""
    try:
        return await drone_service.update_drone(db, drone_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/{drone_id}/telemetry",
    response_model=DroneResponse,
    summary="Update drone telemetry",
)
async def update_telemetry(
    drone_id: int,
    data: DroneTelemetry,
    db: AsyncSession = Depends(get_db),
):
    """
    Update real-time telemetry data for a drone.
    This endpoint is called by the drone's onboard computer — no JWT required
    in a production scenario, you'd use a device API key instead.
    Broadcasts the update via WebSocket to the 'drones' channel.
    """
    try:
        result = await drone_service.update_telemetry(db, drone_id, data)
        # Broadcast telemetry via WebSocket
        await ws_manager.broadcast(
            {
                "event": "telemetry_update",
                "data": result.model_dump(mode="json"),
            },
            channel="drones",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{drone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a drone (admin only)",
    dependencies=[Depends(get_current_admin)],
)
async def delete_drone(
    drone_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete (deactivate) a drone from the fleet."""
    try:
        await drone_service.delete_drone(db, drone_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
