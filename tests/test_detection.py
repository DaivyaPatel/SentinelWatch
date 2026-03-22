"""
Test: Detection service unit tests.
"""

import pytest
from app.services.detection_service import (
    compute_severity,
    determine_incident_type,
)
from app.schemas.incident import DetectionResult


def _make_detection(label: str, confidence: float, incident_type: str) -> DetectionResult:
    """Helper to create a DetectionResult."""
    return DetectionResult(
        label=label,
        confidence=confidence,
        bbox=[0, 0, 100, 100],
        incident_type=incident_type,
    )


def test_compute_severity_fire():
    """Fire detections should have high severity."""
    detections = [_make_detection("fire", 0.95, "fire")]
    severity = compute_severity(detections)
    assert severity >= 7


def test_compute_severity_empty():
    """Empty detections should return severity 1."""
    assert compute_severity([]) == 1


def test_compute_severity_low_confidence():
    """Low confidence should reduce severity."""
    detections = [_make_detection("fire", 0.3, "fire")]
    severity = compute_severity(detections)
    assert severity < 8


def test_determine_incident_type_fire():
    """Fire should be the primary type when present."""
    detections = [
        _make_detection("fire", 0.9, "fire"),
        _make_detection("person", 0.8, "crowd_anomaly"),
    ]
    assert determine_incident_type(detections) == "fire"


def test_determine_incident_type_accident():
    """Accident should be primary when fire is absent."""
    detections = [
        _make_detection("car", 0.85, "accident"),
        _make_detection("person", 0.7, "crowd_anomaly"),
    ]
    assert determine_incident_type(detections) == "accident"


def test_determine_incident_type_empty():
    """Empty detections should return 'other'."""
    assert determine_incident_type([]) == "other"


def test_determine_incident_type_priority():
    """Types should follow priority order: fire > accident > suspicious > crowd."""
    detections = [
        _make_detection("knife", 0.8, "suspicious_activity"),
        _make_detection("person", 0.9, "crowd_anomaly"),
    ]
    # Suspicious activity has higher priority than crowd anomaly
    assert determine_incident_type(detections) == "suspicious_activity"
