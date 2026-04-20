#!/bin/bash

set -e

echo "🚀 Starting DockWatch..."

if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
fi

set -a
source .env
set +a

if [ -z "$DOCKWATCH_JWT_SECRET" ] || [ ${#DOCKWATCH_JWT_SECRET} -lt 32 ]; then
    echo "⚠️  DOCKWATCH_JWT_SECRET not set or too short. Generating one..."
    export DOCKWATCH_JWT_SECRET=$(openssl rand -hex 32)
    sed -i "s|DOCKWATCH_JWT_SECRET=.*|DOCKWATCH_JWT_SECRET=$DOCKWATCH_JWT_SECRET|" .env
    echo "✅ Generated JWT secret (32+ chars)"
fi

echo "🧹 Cleaning up stale networks..."
docker network prune -f 2>/dev/null || true
docker network rm end-sem-project-se_default 2>/dev/null || true

echo "🐳 Building and starting containers..."
docker compose build --parallel
docker compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 8

echo "✅ DockWatch is running!"
echo ""
echo "📋 Access URLs:"
echo "   Frontend: http://localhost:3001"
echo "   Backend:  http://localhost:8001"
echo "   API Docs: http://localhost:8001/docs"
echo ""
echo "🔑 Default credentials: admin / admin123"
echo ""
echo "📝 Useful commands:"
echo "   docker compose logs -f    # View logs"
echo "   ./stop.sh                 # Stop services"
echo "   ./restart.sh              # Restart services"