"""
Test: Dispatch service unit tests.
"""

import pytest
from app.services.dispatch_service import haversine_km, estimate_eta_seconds


def test_haversine_same_point():
    """Distance between same point should be 0."""
    assert haversine_km(28.6139, 77.2090, 28.6139, 77.2090) == 0.0


def test_haversine_known_distance():
    """
    Test Haversine with known distance.
    Delhi (28.6139, 77.2090) to Mumbai (19.0760, 72.8777) ≈ 1,153 km.
    """
    dist = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1100 < dist < 1200  # Approximately 1153 km


def test_haversine_short_distance():
    """Short distance should be reasonable."""
    # About 1km apart
    dist = haversine_km(28.6139, 77.2090, 28.6230, 77.2090)
    assert 0.5 < dist < 2.0


def test_estimate_eta():
    """ETA calculation should be correct."""
    # 15 km at 15 m/s = 1000 seconds
    eta = estimate_eta_seconds(15.0, speed_ms=15.0)
    assert eta == 1000.0


def test_estimate_eta_zero_speed():
    """Zero speed should return infinity."""
    eta = estimate_eta_seconds(10.0, speed_ms=0.0)
    assert eta == float("inf")


def test_estimate_eta_short_distance():
    """Short distance should have short ETA."""
    eta = estimate_eta_seconds(1.0, speed_ms=15.0)
    # 1km = 1000m, at 15 m/s ≈ 66.7 seconds
    assert 60 < eta < 70
