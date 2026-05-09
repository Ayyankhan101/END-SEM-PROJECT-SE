#!/bin/bash
set -e
trap 'set +a 2>/dev/null || true' EXIT

echo "🔄 Restarting DockWatch..."

# Check Docker
docker info > /dev/null 2>&1 || { echo "❌ Docker not running"; exit 1; }

# Generate JWT if needed
if [ -z "$DOCKWATCH_JWT_SECRET" ]; then
    echo "⚠️  DOCKWATCH_JWT_SECRET not set. Generating..."
    export DOCKWATCH_JWT_SECRET=$(openssl rand -hex 32)
fi

# Generate encryption key if needed
if [ -z "$DOCKWATCH_ENCRYPTION_KEY" ]; then
    echo "⚠️  DOCKWATCH_ENCRYPTION_KEY not set. Generating..."
    export DOCKWATCH_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
fi

# Create .env if missing
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Creating..."
    cat > .env << EOF
DOCKWATCH_JWT_SECRET=${DOCKWATCH_JWT_SECRET}
DOCKWATCH_ENCRYPTION_KEY=${DOCKWATCH_ENCRYPTION_KEY}
CORS_ORIGINS=http://localhost:3001,http://localhost:5173
DOCKWATCH_DOCKER_SOCKET=/var/run/docker.sock
EOF
fi

# Load .env
set -a
source .env 2>/dev/null || true
set +a

# Smart rebuild: up with --build uses cache by default
echo "📦 Building and starting services..."
docker compose up -d --build

# Quick health check (max 15s)
echo "⏳ Checking health..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if curl -s --max-time 1 http://localhost:8001/api/health > /dev/null 2>&1; then
        echo "✅ Backend ready"
        break
    fi
    sleep 1
done

echo "✅ DockWatch ready"
echo ""
echo "📍 Frontend: http://localhost:3001"
echo "📍 Backend:  http://localhost:8001"
echo "📝 Logs: docker compose logs -f"