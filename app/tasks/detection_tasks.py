"""
Background detection tasks — processes images via YOLOv8 asynchronously.
"""

import json
import base64
from loguru import logger

from app.tasks.celery_app import celery_app
from app.services.detection_service import (
    run_inference, compute_severity, determine_incident_type,
)


@celery_app.task(
    name="app.tasks.detection_tasks.process_image",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="detection",
)
def process_image(
    self,
    image_base64: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
    source: str = "celery_worker",
):
    """
    Background task: run YOLOv8 inference on a base64-encoded image.

    This is used when detection is offloaded from the API request cycle
    to a Celery worker for better throughput.

    Args:
        image_base64: Base64-encoded image bytes.
        latitude:     GPS latitude of the camera source.
        longitude:    GPS longitude of the camera source.
        source:       Source identifier.

    Returns:
        Dict with detection results, severity, and recommended incident type.
    """
    try:
        logger.info(
            "Processing image from source='{}' at ({}, {})",
            source, latitude, longitude,
        )

        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)

        # Run detection
        detections = run_inference(image_bytes)

        if not detections:
            return {
                "status": "no_threats",
                "detections": [],
                "severity": 0,
                "incident_type": None,
            }

        # Filter threats
        threat_detections = [d for d in detections if d.incident_type != "other"]

        if not threat_detections:
            return {
                "status": "no_threats",
                "detections": [d.model_dump() for d in detections],
                "severity": 0,
                "incident_type": None,
            }

        severity = compute_severity(threat_detections)
        incident_type = determine_incident_type(threat_detections)

        result = {
            "status": "threats_detected",
            "detections": [d.model_dump() for d in detections],
            "threat_count": len(threat_detections),
            "severity": severity,
            "incident_type": incident_type,
            "latitude": latitude,
            "longitude": longitude,
            "source": source,
        }

        logger.info(
            "Detection task complete: {} threats, severity={}, type={}",
            len(threat_detections), severity, incident_type,
        )

        return result

    except Exception as exc:
        logger.error("Detection task failed: {}", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.detection_tasks.process_video_frame_batch",
    bind=True,
    max_retries=2,
    queue="detection",
)
def process_video_frame_batch(
    self,
    frames_base64: list[str],
    latitude: float = 0.0,
    longitude: float = 0.0,
    source: str = "video_stream",
):
    """
    Process a batch of video frames for threat detection.

    Returns results for all frames with the highest-severity detection highlighted.
    """
    try:
        all_results = []
        max_severity = 0
        primary_type = None

        for i, frame_b64 in enumerate(frames_base64):
            image_bytes = base64.b64decode(frame_b64)
            detections = run_inference(image_bytes)

            if detections:
                threats = [d for d in detections if d.incident_type != "other"]
                if threats:
                    severity = compute_severity(threats)
                    if severity > max_severity:
                        max_severity = severity
                        primary_type = determine_incident_type(threats)

                    all_results.append({
                        "frame_index": i,
                        "detections": [d.model_dump() for d in detections],
                        "threat_count": len(threats),
                        "severity": severity,
                    })

        return {
            "status": "batch_complete",
            "frames_processed": len(frames_base64),
            "frames_with_threats": len(all_results),
            "max_severity": max_severity,
            "primary_incident_type": primary_type,
            "results": all_results,
        }

    except Exception as exc:
        logger.error("Batch detection failed: {}", exc)
        raise self.retry(exc=exc)
