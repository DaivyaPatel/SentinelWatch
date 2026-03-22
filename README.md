# 🛡️ AI-Powered Urban Safety System

> Autonomous Drone Dispatch with YOLOv8 Detection, Real-Time WebSockets, and Intelligent Fleet Management

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://docker.com)

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [WebSocket Channels](#websocket-channels)
- [API Examples](#api-examples)
- [Project Structure](#project-structure)
- [Configuration](#configuration)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Application                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌─────────┐ │
│  │   Auth   │  │ Detection │  │ Dispatch │  │Dashboard│ │
│  │  Router  │  │  Router   │  │  Router  │  │ Router  │ │
│  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │              │              │              │      │
│  ┌────┴──────────────┴──────────────┴──────────────┴────┐ │
│  │                   Services Layer                      │ │
│  │  auth │ drone │ incident │ detection │ dispatch │ …   │ │
│  └────┬──────────────┬──────────────┬───────────────────┘ │
│       │              │              │                     │
│  ┌────┴────┐   ┌─────┴─────┐  ┌────┴────┐               │
│  │PostgreSQL│  │   Redis   │  │ YOLOv8  │               │
│  │   (DB)   │  │  (Queue)  │  │  (AI)   │               │
│  └──────────┘  └───────────┘  └─────────┘               │
│                                                          │
│  WebSocket Channels: /ws/drones │ /ws/incidents │ /ws/…  │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and navigate
cd urban-safety-system

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
docker-compose up --build -d

# 4. Seed sample data
docker-compose exec app python -m scripts.seed_data

# 5. Open Swagger docs
# http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup PostgreSQL and Redis (must be running)
# Update .env with your connection strings

# 4. Copy environment config
cp .env.example .env

# 5. Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Seed sample data (in another terminal)
python -m scripts.seed_data

# 7. Open Swagger docs
# http://localhost:8000/docs
```

### Running Celery Worker (for background tasks)

```bash
celery -A app.tasks.celery_app worker --loglevel=info -Q detection,notifications
```

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Login and get JWT token |
| GET | `/api/v1/auth/me` | Get current user profile |
| GET | `/api/v1/auth/users` | List all users (admin) |

### Drone Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/drones` | Register a new drone |
| GET | `/api/v1/drones` | List all drones |
| GET | `/api/v1/drones/{id}` | Get drone details |
| PATCH | `/api/v1/drones/{id}` | Update drone info |
| PUT | `/api/v1/drones/{id}/telemetry` | Update drone telemetry |
| DELETE | `/api/v1/drones/{id}` | Deactivate drone (admin) |

### Incident Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/incidents` | Report an incident |
| GET | `/api/v1/incidents` | List incidents |
| GET | `/api/v1/incidents/stats` | Incident statistics |
| GET | `/api/v1/incidents/timeline` | Incident timeline |
| GET | `/api/v1/incidents/{id}` | Get incident details |
| PATCH | `/api/v1/incidents/{id}` | Update incident |

### AI Detection
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/detection/analyze` | Analyze image for threats |
| POST | `/api/v1/detection/analyze-batch` | Batch image analysis |

### Dispatch & Routing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/dispatch` | Dispatch drone to incident |
| GET | `/api/v1/dispatch/route/{drone_id}/{incident_id}` | Plan flight route |

### Geofencing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/geofencing/check` | Check coordinate vs no-fly zones |
| GET | `/api/v1/geofencing/zones` | List no-fly zones |
| POST | `/api/v1/geofencing/zones` | Create no-fly zone (admin) |
| DELETE | `/api/v1/geofencing/zones/{id}` | Delete no-fly zone (admin) |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/alerts` | Create an alert |
| GET | `/api/v1/alerts` | List alerts |
| GET | `/api/v1/alerts/unread-count` | Get unread count |
| PATCH | `/api/v1/alerts/{id}` | Update alert |
| POST | `/api/v1/alerts/mark-all-read` | Mark all as read |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/overview` | System overview |
| GET | `/api/v1/dashboard/incident-timeline` | Timeline view |
| GET | `/api/v1/dashboard/logs` | System logs |

---

## 🔌 WebSocket Channels

| Endpoint | Events | Description |
|----------|--------|-------------|
| `/ws/drones` | `telemetry_update`, `drone_dispatched` | Live drone tracking |
| `/ws/incidents` | `new_incident`, `incident_updated`, `drone_dispatched` | Incident updates |
| `/ws/alerts` | `new_alert` | Alert notifications |
| `/ws/all` | All events | Unified feed |

**Connect with JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/all');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event, 'Data:', data.data);
};
```

---

## 📝 API Examples

### Register User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "email": "john@example.com", "password": "SecurePass123!", "role": "operator"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```
Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": { "id": 1, "username": "admin", "role": "admin" }
}
```

### Register Drone
```bash
curl -X POST http://localhost:8000/api/v1/drones \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Drone-Foxtrot-06", "model": "DJI-Matrice-300", "latitude": 28.6139, "longitude": 77.2090}'
```

### Report Incident (auto-dispatches if severity ≥ 7)
```bash
curl -X POST http://localhost:8000/api/v1/incidents \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "fire",
    "severity": 8,
    "latitude": 28.6200,
    "longitude": 77.2150,
    "description": "Fire detected near building",
    "confidence_score": 0.92,
    "source": "camera_001"
  }'
```

### Dispatch Drone
```bash
curl -X POST http://localhost:8000/api/v1/dispatch \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"incident_id": 1}'
```
Response:
```json
{
  "success": true,
  "incident_id": 1,
  "assigned_drone_id": 1,
  "drone_name": "Drone-Alpha-01",
  "distance_km": 2.45,
  "estimated_eta_seconds": 163.3,
  "message": "Drone 'Drone-Alpha-01' dispatched successfully"
}
```

### Analyze Image
```bash
curl -X POST http://localhost:8000/api/v1/detection/analyze \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@image.jpg" \
  -F "latitude=28.62" \
  -F "longitude=77.21" \
  -F "source=camera_001"
```

---

## 📁 Project Structure

```
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── core/
│   │   ├── config.py              # Pydantic settings
│   │   ├── database.py            # Async SQLAlchemy
│   │   ├── security.py            # JWT + bcrypt
│   │   ├── dependencies.py        # FastAPI DI helpers
│   │   ├── logging_config.py      # Loguru setup
│   │   └── websocket_manager.py   # WS connection manager
│   ├── models/
│   │   ├── user.py                # User model
│   │   ├── drone.py               # Drone model
│   │   ├── incident.py            # Incident model
│   │   ├── alert.py               # Alert model
│   │   ├── log.py                 # SystemLog model
│   │   └── geofence.py            # NoFlyZone model
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── services/                  # Business logic layer
│   ├── routers/                   # API route handlers
│   └── tasks/                     # Celery background tasks
├── scripts/
│   └── seed_data.py               # Database seeder
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Configuration

All settings are managed via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `JWT_SECRET_KEY` | `change-me...` | JWT signing secret |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token TTL |
| `YOLO_MODEL_PATH` | `yolov8n.pt` | Path to YOLO weights |
| `YOLO_CONFIDENCE_THRESHOLD` | `0.5` | Minimum confidence |
| `DRONE_BATTERY_THRESHOLD` | `20` | Min battery % for dispatch |
| `MAX_DISPATCH_DISTANCE_KM` | `50` | Max dispatch radius |

---

## 🔐 Default Credentials (After Seeding)

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Operator | `operator_01` | `operator123` |

---

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app
```

---

Built with ❤️ for urban safety using AI + autonomous systems.
