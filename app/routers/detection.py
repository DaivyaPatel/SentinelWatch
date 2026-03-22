"""
AI Detection router — image upload and YOLOv8 inference endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.incident import (
    IncidentCreate, DetectionResponse, DetectionResult,
)
from app.services import detection_service, incident_service

router = APIRouter(prefix="/detection", tags=["AI Detection"])


@router.post(
    "/analyze",
    response_model=DetectionResponse,
    summary="Analyze an image for safety threats",
    responses={
        200: {
            "description": "Detection results",
            "content": {
                "application/json": {
                    "example": {
                        "detections": [
                            {
                                "label": "fire",
                                "confidence": 0.9234,
                                "bbox": [120.5, 80.3, 350.2, 290.7],
                                "incident_type": "fire",
                            }
                        ],
                        "total_detections": 1,
                        "incident_created": True,
                        "incident_id": 5,
                    }
                }
            },
        },
    },
)
async def analyze_image(
    file: UploadFile = File(..., description="JPEG/PNG image from CCTV or drone"),
    latitude: float = 0.0,
    longitude: float = 0.0,
    source: str = "unknown",
    auto_create_incident: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an image for YOLOv8 safety threat detection.

    The system will:
    1. Run YOLOv8 inference to detect fires, accidents, etc.
    2. Optionally create an incident record if threats are found.
    3. Return bounding boxes, confidence scores, and classifications.

    Query params:
    - `latitude` / `longitude`: GPS coordinates of the camera/drone.
    - `source`: Identifier for the feed source (e.g. 'camera_001').
    - `auto_create_incident`: If True (default), automatically create
      an incident when threats are detected.
    """
    # Validate file type
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG images are supported",
        )

    # Read image bytes
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Run YOLOv8 inference
    detections = detection_service.run_inference(image_bytes)

    incident_created = False
    incident_id = None

    # Auto-create incident if threats detected
    if detections and auto_create_incident:
        # Filter out generic 'other' detections
        threat_detections = [d for d in detections if d.incident_type != "other"]

        if threat_detections:
            severity = detection_service.compute_severity(threat_detections)
            primary_type = detection_service.determine_incident_type(threat_detections)

            # Build detection metadata
            metadata = {
                "detections": [d.model_dump() for d in detections],
                "source_file": file.filename,
                "total_objects": len(detections),
            }

            incident_data = IncidentCreate(
                incident_type=primary_type,
                severity=severity,
                latitude=latitude,
                longitude=longitude,
                description=f"AI-detected {primary_type} with {len(threat_detections)} threat(s)",
                confidence_score=max(d.confidence for d in threat_detections),
                detection_metadata=metadata,
                source=source,
            )

            incident = await incident_service.create_incident(db, incident_data)
            incident_created = True
            incident_id = incident.id

    return DetectionResponse(
        detections=detections,
        total_detections=len(detections),
        incident_created=incident_created,
        incident_id=incident_id,
    )


@router.post(
    "/analyze-batch",
    response_model=list[DetectionResponse],
    summary="Analyze multiple images",
)
async def analyze_batch(
    files: list[UploadFile] = File(..., description="Multiple images"),
    latitude: float = 0.0,
    longitude: float = 0.0,
    source: str = "unknown",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze multiple images in a single request. Useful for video frame batches."""
    results = []
    for file in files:
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            continue

        detections = detection_service.run_inference(image_bytes)
        results.append(DetectionResponse(
            detections=detections,
            total_detections=len(detections),
            incident_created=False,
            incident_id=None,
        ))

    return results
