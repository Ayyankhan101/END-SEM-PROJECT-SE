#!/bin/bash
set -e

echo "🔄 Restarting DockWatch..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if JWT_SECRET is set
if [ -z "$DOCKWATCH_JWT_SECRET" ]; then
    echo "⚠️  DOCKWATCH_JWT_SECRET not set. Generating one..."
    export DOCKWATCH_JWT_SECRET=$(openssl rand -hex 32)
    echo "✅ Generated JWT_SECRET"
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cat > .env << EOF
# DockWatch Environment Variables
# Auto-generated on $(date)

# REQUIRED: JWT Secret for authentication (generate with: openssl rand -hex 32)
DOCKWATCH_JWT_SECRET=${DOCKWATCH_JWT_SECRET}

# Optional: CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:3001,http://localhost:5173

# Optional: Docker socket path
DOCKWATCH_DOCKER_SOCKET=/var/run/docker.sock
EOF
    echo "✅ Created .env file"
fi

# Load .env if exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Build and start containers
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check health
if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed. Check logs with: docker compose logs backend"
fi

echo "✅ DockWatch restarted"
echo ""
echo "📍 Services:"
echo "   Frontend: http://localhost:3001"
echo "   Backend:  http://localhost:8001"
echo ""
echo "📝 To view logs: docker compose logs -f"