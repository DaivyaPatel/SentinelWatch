"""
Geofencing router — no-fly zone management and coordinate validation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.dispatch import (
    GeofenceCheckRequest, GeofenceCheckResponse,
    NoFlyZoneCreate, NoFlyZoneResponse,
)
from app.services import geofencing_service

router = APIRouter(prefix="/geofencing", tags=["Geofencing"])


@router.post(
    "/check",
    response_model=GeofenceCheckResponse,
    summary="Check if a coordinate is in a no-fly zone",
)
async def check_geofence(
    data: GeofenceCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validate whether a GPS coordinate falls inside any active no-fly zone."""
    return await geofencing_service.check_geofence(db, data.latitude, data.longitude)


@router.get(
    "/zones",
    response_model=list[NoFlyZoneResponse],
    summary="List all no-fly zones",
)
async def list_zones(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all registered no-fly zones."""
    return await geofencing_service.list_no_fly_zones(db, active_only)


@router.post(
    "/zones",
    response_model=NoFlyZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a no-fly zone",
    dependencies=[Depends(get_current_admin)],
)
async def create_zone(
    data: NoFlyZoneCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new no-fly zone (admin only)."""
    try:
        return await geofencing_service.create_no_fly_zone(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a no-fly zone",
    dependencies=[Depends(get_current_admin)],
)
async def delete_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a no-fly zone (admin only)."""
    try:
        await geofencing_service.delete_no_fly_zone(db, zone_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
