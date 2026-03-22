import cv2
import json
import time
from collections import defaultdict
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

# map yolo classes to incident types
INCIDENT_MAP = {
    "person":    "fallen_individual",
    "car":       "suspicious_vehicle",
    "truck":     "suspicious_vehicle",
    "backpack":  "abandoned_object",
    "suitcase":  "abandoned_object",
    "handbag":   "abandoned_object",
}

CONFIDENCE_THRESHOLD = 0.6
COOLDOWN_SECONDS = 5
MULTIFRAME_MIN = 3  # must appear in 3 consecutive frames to confirm

def analyze_behavior(track_history, class_name):
    """basic behavior analysis based on movement patterns"""
    if len(track_history) < 5:
        return None
    
    positions = track_history[-5:]
    movement = sum(
        abs(positions[i][0] - positions[i-1][0]) + abs(positions[i][1] - positions[i-1][1])
        for i in range(1, len(positions))
    )

    if class_name == "person" and movement < 5:
        return "fallen_individual"  # person not moving = possibly fallen
    if class_name in ["backpack", "suitcase"] and movement < 2:
        return "abandoned_object"   # object stationary = possibly abandoned
    if class_name in ["car", "truck"] and movement < 3:
        return "suspicious_vehicle" # vehicle not moving = suspicious stop

    return None

def detect(video_path="test.mp4"):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0

    alerts = []
    last_alert_time = {}
    frame_counts = defaultdict(int)   # multiframe validation counter
    track_history = defaultdict(list) # behavior analysis history

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        timestamp = round(frame_count / fps, 2)

        results = model.track(frame, conf=CONFIDENCE_THRESHOLD, persist=True, verbose=False)[0]

        if results.boxes.id is None:
            cv2.imshow("SentinelWatch Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        for box, track_id, cls, conf in zip(
            results.boxes.xyxy,
            results.boxes.id,
            results.boxes.cls,
            results.boxes.conf
        ):
            class_name = model.names[int(cls)]
            track_id   = int(track_id)
            confidence = float(conf)

            if class_name not in INCIDENT_MAP:
                continue

            # track position history for behavior analysis
            cx = float((box[0] + box[2]) / 2)
            cy = float((box[1] + box[3]) / 2)
            track_history[track_id].append((cx, cy))
            if len(track_history[track_id]) > 30:
                track_history[track_id].pop(0)

            # behavior-based incident type (overrides class map if triggered)
            behavior = analyze_behavior(track_history[track_id], class_name)
            incident_type = behavior if behavior else INCIDENT_MAP[class_name]

            # multiframe validation — must appear in 3+ consecutive frames
            frame_counts[track_id] += 1
            if frame_counts[track_id] < MULTIFRAME_MIN:
                continue

            # cooldown check
            last_time = last_alert_time.get(incident_type, -999)
            if timestamp - last_time < COOLDOWN_SECONDS:
                continue

            last_alert_time[incident_type] = timestamp

            alert = {
                "type":       incident_type,
                "timestamp":  timestamp,
                "confidence": round(confidence, 2),
                "frame":      frame_count,
                "track_id":   track_id,
                "behavior_triggered": behavior is not None,
                "location": {
                    "x": round(cx, 1),
                    "y": round(cy, 1)
                }
            }

            print(f"[ALERT] {json.dumps(alert)}")
            alerts.append(alert)

        cv2.imshow("SentinelWatch Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return alerts

if __name__ == "__main__":
    results = detect("test.mp4")
    with open("alerts.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nTotal alerts: {len(results)}")
    print("Saved to alerts.json")