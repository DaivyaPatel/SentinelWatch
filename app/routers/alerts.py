"""
Alert router — CRUD and notification management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.alert import (
    AlertCreate, AlertUpdate,
    AlertResponse, AlertListResponse,
)
from app.schemas.common import MessageResponse
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])


@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an alert",
)
async def create_alert(
    data: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually create an alert (auto-pushes via WebSocket)."""
    return await alert_service.create_alert(db, data)


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List alerts",
)
async def list_alerts(
    priority: Optional[str] = None,
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alerts with optional filters."""
    return await alert_service.list_alerts(db, priority, is_read, skip, limit)


@router.get(
    "/unread-count",
    summary="Get unread alert count",
)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the number of unread alerts."""
    count = await alert_service.get_unread_count(db)
    return {"unread_count": count}


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert details",
)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a single alert by ID."""
    try:
        return await alert_service.get_alert_by_id(db, alert_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Update an alert",
)
async def update_alert(
    alert_id: int,
    data: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update alert properties (e.g. mark as read)."""
    try:
        return await alert_service.update_alert(db, alert_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/mark-all-read",
    response_model=MessageResponse,
    summary="Mark all alerts as read",
)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all unread alerts as read."""
    count = await alert_service.mark_all_read(db)
    return MessageResponse(message=f"Marked {count} alert(s) as read")
