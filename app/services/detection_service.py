"""
AI Detection service — YOLOv8 inference on images/frames.

Uses Ultralytics YOLOv8 for object detection and maps detected classes
to urban safety incident categories.
"""

import io
import math
from typing import Optional

import cv2
import numpy as np
from loguru import logger

from app.core.config import get_settings
from app.schemas.incident import DetectionResult

settings = get_settings()

# ---------------------------------------------------------------------------
# Class-to-incident mapping
# ---------------------------------------------------------------------------
# Maps COCO / custom YOLO class names to our incident categories
CLASS_TO_INCIDENT = {
    # Fire-related
    "fire": "fire",
    "smoke": "fire",
    "flame": "fire",
    # Accident-related
    "car": "accident",
    "truck": "accident",
    "bus": "accident",
    "motorcycle": "accident",
    # Suspicious activity
    "knife": "suspicious_activity",
    "gun": "suspicious_activity",
    "weapon": "suspicious_activity",
    # Crowd anomaly (detected via person density)
    "person": "crowd_anomaly",
}

# Minimum number of 'person' detections to trigger a crowd anomaly
CROWD_THRESHOLD = 10

# Singleton model holder (loaded lazily)
_model = None


def _load_model():
    """Lazy-load the YOLOv8 model (expensive, do once)."""
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
            _model = YOLO(settings.YOLO_MODEL_PATH)
            logger.info("YOLOv8 model loaded: {}", settings.YOLO_MODEL_PATH)
        except Exception as e:
            logger.error("Failed to load YOLO model: {}", e)
            _model = None
    return _model


def run_inference(image_bytes: bytes) -> list[DetectionResult]:
    """
    Run YOLOv8 object detection on raw image bytes.

    Args:
        image_bytes: Raw bytes of the image (JPEG, PNG, etc.)

    Returns:
        List of DetectionResult objects with labels, confidence,
        bounding boxes, and mapped incident types.
    """
    model = _load_model()
    if model is None:
        logger.warning("YOLO model not available — returning empty detections")
        return []

    # Decode image from bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        logger.error("Failed to decode image bytes")
        return []

    # Run inference
    results = model(image, conf=settings.YOLO_CONFIDENCE_THRESHOLD, verbose=False)

    detections: list[DetectionResult] = []
    person_count = 0

    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for i in range(len(boxes)):
            # Extract bounding box
            xyxy = boxes.xyxy[i].cpu().numpy().tolist()
            confidence = float(boxes.conf[i].cpu().numpy())
            class_id = int(boxes.cls[i].cpu().numpy())
            class_name = model.names.get(class_id, "unknown")

            # Map class to incident type
            incident_type = CLASS_TO_INCIDENT.get(class_name, "other")

            if class_name == "person":
                person_count += 1

            detections.append(DetectionResult(
                label=class_name,
                confidence=round(confidence, 4),
                bbox=[round(x, 2) for x in xyxy],
                incident_type=incident_type,
            ))

    # If many people detected, flag highest severity detection as crowd anomaly
    if person_count >= CROWD_THRESHOLD:
        # Add a synthetic crowd_anomaly detection
        detections.append(DetectionResult(
            label="crowd_anomaly",
            confidence=min(1.0, person_count / (CROWD_THRESHOLD * 2)),
            bbox=[0, 0, image.shape[1], image.shape[0]],  # Full frame
            incident_type="crowd_anomaly",
        ))

    logger.info(
        "Detection complete: {} objects found, {} persons",
        len(detections), person_count,
    )
    return detections


def compute_severity(detections: list[DetectionResult]) -> int:
    """
    Compute a severity score (1-10) based on detection results.

    Scoring heuristics:
        - Fire → base 8
        - Accident → base 7
        - Suspicious activity → base 6
        - Crowd anomaly → base 5
        - Other → base 3
    Adjusted by average confidence.
    """
    if not detections:
        return 1

    severity_map = {
        "fire": 8,
        "accident": 7,
        "suspicious_activity": 6,
        "crowd_anomaly": 5,
        "other": 3,
    }

    # Use the highest-severity incident type present
    max_base = max(
        severity_map.get(d.incident_type, 3)
        for d in detections
    )

    # Boost with average confidence
    avg_confidence = sum(d.confidence for d in detections) / len(detections)
    severity = min(10, max(1, round(max_base * avg_confidence + len(detections) * 0.1)))

    return severity


def determine_incident_type(detections: list[DetectionResult]) -> str:
    """
    Determine the primary incident type from a list of detections.
    Returns the type with the highest severity mapping.
    """
    if not detections:
        return "other"

    priority_order = ["fire", "accident", "suspicious_activity", "crowd_anomaly", "other"]

    types_found = set(d.incident_type for d in detections)
    for t in priority_order:
        if t in types_found:
            return t
    return "other"
