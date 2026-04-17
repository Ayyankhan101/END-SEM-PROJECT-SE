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

if [ -z "$DOCKWATCH_JWT_SECRET" ]; then
    echo "⚠️  DOCKWATCH_JWT_SECRET not set. Generating one..."
    export DOCKWATCH_JWT_SECRET=$(openssl rand -base64 32)
    echo "DOCKWATCH_JWT_SECRET=$DOCKWATCH_JWT_SECRET" >> .env
    echo "✅ Generated JWT secret"
fi

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