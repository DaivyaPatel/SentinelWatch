"""
System logging service — persists structured log entries to the database.
"""

from typing import Optional, Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import SystemLog, LogLevel


async def create_log(
    db: AsyncSession,
    level: str,
    module: str,
    action: str,
    message: str,
    metadata: Optional[dict[str, Any]] = None,
) -> SystemLog:
    """Create a structured log entry in the database."""
    log = SystemLog(
        level=LogLevel(level),
        module=module,
        action=action,
        message=message,
        metadata=metadata or {},
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_logs(
    db: AsyncSession,
    level: Optional[str] = None,
    module: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SystemLog]:
    """Query logs with optional filters."""
    query = select(SystemLog)

    if level:
        query = query.where(SystemLog.level == LogLevel(level))
    if module:
        query = query.where(SystemLog.module == module)

    query = query.offset(skip).limit(limit).order_by(desc(SystemLog.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_log_stats(db: AsyncSession) -> dict:
    """Aggregate log statistics by level."""
    stats = {}
    for level in LogLevel:
        count = (
            await db.execute(
                select(func.count(SystemLog.id)).where(SystemLog.level == level)
            )
        ).scalar() or 0
        stats[level.value] = count

    total = (await db.execute(select(func.count(SystemLog.id)))).scalar() or 0
    stats["total"] = total
    return stats
