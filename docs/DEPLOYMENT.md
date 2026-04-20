# Deployment Guide

## Prerequisites

### Backend
- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

### Frontend (Development)
- Node.js 18+
- npm 9+

Run locally: `npm install && npm run dev`

Or use Docker: Already included in docker-compose.yml

## Production Deployment

### 1. Environment Setup

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with secure values:

```env
DOCKWATCH_JWT_SECRET=your-secure-random-string-at-least-32-chars
CORS_ORIGINS=http://localhost:3000,https://your-domain.com
```

Generate a secure JWT secret:
```bash
openssl rand -base64 32
```

### 2. Build and Start

#### Backend Only
```bash
docker-compose up -d --build
```

#### Frontend (Development)

```bash
cd frontend
npm install
npm run dev
```

#### Frontend (Production Build)

```bash
cd frontend
npm install
npm run build
npm run preview
```

### 3. Verify Deployment

### 4. Verify Deployment

Check service status:
```bash
docker-compose ps
```

Check logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5. Access the Application

**Development:**
- Frontend: http://localhost:5173 (Vite dev server)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Production (Docker):**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### 5. Default Credentials

- Username: `admin`
- Password: `admin123`

**Important:** Change the default password in production!

## Docker Swarm Deployment

### 1. Initialize Swarm

```bash
docker swarm init
```

### 2. Create Overlay Network

```bash
docker network create --driver overlay dockwatch-network
```

### 3. Deploy Stack

```bash
docker stack deploy -c docker-compose.yml dockwatch
```

### 4. Verify

```bash
docker stack ps dockwatch
```

## Production Considerations

### Security

1. **Change default credentials**: Update the admin password in the database
2. **Use HTTPS**: Set up reverse proxy with SSL/TLS
3. **Restrict CORS**: Update allowed origins for your domain
4. **Secret management**: Use Docker secrets or external secret management

### Monitoring

The stack includes health checks:
- Backend: `/api/health`
- Frontend: HTTP check on port 3000

### Backup

Backup the SQLite database:
```bash
docker-compose exec backend cp /app/data/dockwatch.db /app/data/dockwatch-backup.db
```

### Updates

```bash
docker-compose pull
docker-compose up -d
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs backend
```

### Network overlap error

If you see `Pool overlaps with other network` error:

```bash
docker network prune
```

Or remove conflicting network manually:
```bash
docker network ls
docker network rm <network-name>
```

### Database issues

Reset database:
```bash
docker-compose down -v
docker-compose up -d
```

### Docker socket permission

On Linux, ensure user has docker access:
```bash
sudo usermod -aG docker $USER
```

## Scaling

For horizontal scaling:

1. Use PostgreSQL instead of SQLite
2. Use Redis for WebSocket scaling
3. Set up load balancer

Example PostgreSQL configuration:

```yaml
backend:
  environment:
    - DATABASE_URL=postgresql://user:pass@postgres:5432/dockwatch
```