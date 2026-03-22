"""
Celery application configuration.
Uses Redis as both broker and result backend.
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "urban_safety_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task behaviour
    task_track_started=True,
    task_acks_late=True,              # Ack after task completes (fault-tolerant)
    worker_prefetch_multiplier=1,     # One task at a time for long-running tasks

    # Result expiration
    result_expires=3600,              # Results expire after 1 hour

    # Task routing
    task_routes={
        "app.tasks.detection_tasks.*": {"queue": "detection"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
    },
)

# Auto-discover task modules
celery_app.autodiscover_tasks(["app.tasks"])
