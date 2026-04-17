# DockWatch - Docker Container Health Monitoring System

A real-time Docker container monitoring and management dashboard with auto-recovery capabilities.

## Features

- **Real-time Monitoring**: Track CPU, memory, and network metrics for all Docker containers
- **Auto-Recovery**: Automatic container restart on failure detection
- **WebSocket Updates**: Live container status updates without page refresh
- **Container Management**: Start, stop, pause, unpause, and create containers
- **Stack Management**: Deploy and manage Docker Compose stacks
- **Multi-Host Support**: Connect to remote Docker hosts
- **Alerting System**: Configurable threshold alerts for CPU and memory usage
- **Historical Metrics**: Store and visualize container metrics over time

## Tech Stack

- **Backend**: FastAPI (Python), SQLAlchemy, Docker SDK
- **Frontend**: React 18, Vite, Tailwind CSS, Recharts
- **Real-time**: Socket.IO for WebSocket communication
- **Database**: SQLite (easily swappable to PostgreSQL)

## Quick Start

### Prerequisites

- Docker and Docker Compose

### One-Command Start

```bash
./start.sh
```

This will:
1. Create `.env` file if it doesn't exist
2. Generate a secure JWT secret if not set
3. Build and start all services
4. Display access URLs and credentials

### Available Scripts

| Command | Description |
|---------|-------------|
| `./start.sh` | Start all services |
| `./stop.sh` | Stop all services |
| `./status.sh` | Check service status |

### Default Login

- Username: `admin`
- Password: `admin123`

### Access URLs

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
export DOCKWATCH_JWT_SECRET="your-secret"
python -m app.main
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Configuration

Configuration is managed via `config/config.yaml`:

```yaml
docker:
  socket_path: "/var/run/docker.sock"
  poll_interval: 5

monitoring:
  cpu_threshold: 90
  memory_threshold: 90

recovery:
  enabled: true

database:
  metrics_ttl_days: 7

cors:
  allowed_origins:
    - "http://localhost:3000"
    - "http://localhost:5173"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/token | Login |
| GET | /api/containers | List containers |
| GET | /api/containers/{id} | Container details |
| GET | /api/containers/{id}/metrics | Container metrics |
| POST | /api/containers/{id}/restart | Restart container |
| POST | /api/containers/{id}/pause | Pause container |
| POST | /api/containers/{id}/unpause | Unpause container |
| GET | /api/containers/{id}/logs | Get container logs |
| POST | /api/containers | Create container |
| GET | /api/stacks | List stacks |
| POST | /api/stacks | Deploy stack |
| GET | /api/hosts | List hosts |
| POST | /api/hosts | Add host |
| GET | /api/alerts | List alerts |
| GET | /api/settings | Get settings |
| PUT | /api/settings | Update settings |

## WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `connect` | Server | Connection established |
| `pong` | Server | Response to ping |
| `metrics` | Server | Real-time metrics update |
| `container_update` | Server | Container state change |
| `alert` | Server | New alert notification |
| `ping` | Client | Heartbeat ping |

## Rate Limiting

API endpoints are rate-limited:
- Login: 10 requests/minute
- Authenticated endpoints: 60 requests/minute
- Write operations: 10-30 requests/minute

## License

MIT