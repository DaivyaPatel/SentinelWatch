"""
Alert service — creation, push via WebSocket, and management.
"""

from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.alert import Alert, AlertPriority
from app.schemas.alert import (
    AlertCreate, AlertUpdate,
    AlertResponse, AlertListResponse,
)
from app.core.websocket_manager import ws_manager


async def create_alert(
    db: AsyncSession, data: AlertCreate, push_ws: bool = True
) -> AlertResponse:
    """
    Create an alert and optionally push it via WebSocket.

    Args:
        db:      Database session.
        data:    Alert creation payload.
        push_ws: If True, broadcast the alert to the 'alerts' WS channel.
    """
    alert = Alert(
        incident_id=data.incident_id,
        priority=AlertPriority(data.priority),
        title=data.title,
        message=data.message,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)

    logger.info(
        "Alert created: id={} priority={} incident_id={}",
        alert.id, alert.priority, alert.incident_id,
    )

    response = AlertResponse.model_validate(alert)

    # Push to WebSocket subscribers
    if push_ws:
        await ws_manager.broadcast(
            {
                "event": "new_alert",
                "data": response.model_dump(mode="json"),
            },
            channel="alerts",
        )

    return response


async def get_alert_by_id(db: AsyncSession, alert_id: int) -> AlertResponse:
    """
    Fetch a single alert.

    Raises:
        ValueError: If not found.
    """
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise ValueError(f"Alert with id {alert_id} not found")
    return AlertResponse.model_validate(alert)


async def list_alerts(
    db: AsyncSession,
    priority: Optional[str] = None,
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> AlertListResponse:
    """List alerts with optional filters and pagination."""
    query = select(Alert)
    count_query = select(func.count(Alert.id))

    if priority:
        query = query.where(Alert.priority == AlertPriority(priority))
        count_query = count_query.where(Alert.priority == AlertPriority(priority))
    if is_read is not None:
        query = query.where(Alert.is_read == is_read)
        count_query = count_query.where(Alert.is_read == is_read)

    query = query.offset(skip).limit(limit).order_by(desc(Alert.created_at))
    result = await db.execute(query)
    alerts = result.scalars().all()

    total = (await db.execute(count_query)).scalar() or 0

    return AlertListResponse(
        total=total,
        alerts=[AlertResponse.model_validate(a) for a in alerts],
    )


async def update_alert(
    db: AsyncSession, alert_id: int, data: AlertUpdate
) -> AlertResponse:
    """
    Partially update an alert (e.g. mark as read).

    Raises:
        ValueError: If not found.
    """
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise ValueError(f"Alert with id {alert_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "priority" and value is not None:
            setattr(alert, field, AlertPriority(value))
        else:
            setattr(alert, field, value)

    await db.flush()
    await db.refresh(alert)

    logger.info("Alert updated: id={} fields={}", alert_id, list(update_data.keys()))
    return AlertResponse.model_validate(alert)


async def mark_all_read(db: AsyncSession) -> int:
    """Mark all unread alerts as read. Returns count of updated alerts."""
    result = await db.execute(
        select(Alert).where(Alert.is_read == False)
    )
    alerts = result.scalars().all()
    count = 0
    for alert in alerts:
        alert.is_read = True
        count += 1
    await db.flush()

    logger.info("Marked {} alerts as read", count)
    return count


async def get_unread_count(db: AsyncSession) -> int:
    """Return the count of unread alerts."""
    result = await db.execute(
        select(func.count(Alert.id)).where(Alert.is_read == False)
    )
    return result.scalar() or 0
