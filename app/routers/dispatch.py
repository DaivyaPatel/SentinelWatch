"""
Dispatch & routing router — drone dispatch and path planning endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.dispatch import DispatchRequest, DispatchResponse, RouteResponse
from app.services import dispatch_service, routing_service
from app.services import drone_service, incident_service

router = APIRouter(prefix="/dispatch", tags=["Dispatch & Routing"])


@router.post(
    "",
    response_model=DispatchResponse,
    summary="Dispatch a drone to an incident",
    responses={
        200: {
            "description": "Dispatch result",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "incident_id": 1,
                        "assigned_drone_id": 3,
                        "drone_name": "Drone-Alpha-01",
                        "distance_km": 2.45,
                        "estimated_eta_seconds": 163.3,
                        "message": "Drone 'Drone-Alpha-01' dispatched successfully",
                    }
                }
            },
        },
    },
)
async def dispatch(
    data: DispatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dispatch the best available drone to an incident.

    The engine uses Haversine distance, battery level, and incident severity
    to score and rank available drones. Supports optional force-assignment.
    """
    return await dispatch_service.dispatch_drone(db, data)


@router.get(
    "/route/{drone_id}/{incident_id}",
    response_model=RouteResponse,
    summary="Plan a route from drone to incident",
)
async def plan_route(
    drone_id: int,
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a geofence-aware flight path from a drone to an incident.

    Returns waypoints, total distance, ETA, and geofence clearance status.
    Automatically reroutes if the path crosses a no-fly zone.
    """
    try:
        drone = await drone_service.get_drone_by_id(db, drone_id)
        incident = await incident_service.get_incident_by_id(db, incident_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return await routing_service.plan_route(
        db,
        drone_id=drone.id,
        drone_lat=drone.latitude,
        drone_lon=drone.longitude,
        incident_id=incident.id,
        incident_lat=incident.latitude,
        incident_lon=incident.longitude,
    )
