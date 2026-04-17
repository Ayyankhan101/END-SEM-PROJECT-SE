#!/bin/bash

echo "📊 DockWatch Status"
echo "==================="

echo ""
echo "Container Status:"
docker compose ps

echo ""
echo "Backend Health:"
curl -s http://localhost:8001/api/health 2>/dev/null | grep -q "healthy" && echo "✅ Backend: Healthy" || echo "❌ Backend: Unhealthy"

echo ""
echo "Frontend:"
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 | grep -q "200" && echo "✅ Frontend: Running" || echo "❌ Frontend: Not responding"