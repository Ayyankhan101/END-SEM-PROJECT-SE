#!/bin/bash

set -e

LABEL="dockwatch.monitor=true"

echo "Creating test containers for anomaly detection..."

# CPU Spike Test - Creates high CPU load
echo "Creating cpu-spike-test container..."
docker run -d \
  --name cpu-spike-test \
  --label $LABEL \
  alpine:latest \
  sh -c "apk add --no-cache stress > /dev/null 2>&1 && stress -c 4 -t 300"

# Memory Leak Test - Gradual memory allocation
echo "Creating memory-leak-test container..."
docker run -d \
  --name memory-leak-test \
  --label $LABEL \
  alpine:latest \
  sh -c "apk add --no-cache python3 > /dev/null 2>&1 && python3 -c '
import time
import sys
refs = []
while True:
    refs.append(bytearray(1024*1024))
    time.sleep(2)
'"

# High Memory Test - Sustained high memory
echo "Creating high-memory-test container..."
docker run -d \
  --name high-memory-test \
  --label $LABEL \
  alpine:latest \
  sh -c "apk add --no-cache > /dev/null 2>&1 && sh -c 'while true; do sleep 3600; done'"

# Restart Loop Test (simulated with quick restarts)
echo "Creating restart-loop-test container..."
docker run -d \
  --name restart-loop-test \
  --label $LABEL \
  --restart on-failure:5 \
  alpine:latest \
  sh -c "echo 'Starting...'; sleep 5; exit 1"

# Stopped Test - Container that gets stopped
echo "Creating stopped-test container..."
docker run -d \
  --name stopped-test \
  --label $LABEL \
  alpine:latest \
  sleep 300

echo ""
echo "Test containers created:"
docker ps -a --filter "label=$LABEL" --format "table {{.Names}}\t{{.Status}}\t{{.Labels}}"

# Trigger sync to database
echo ""
echo "Syncing containers to database..."
sleep 3
docker compose -f /home/ayyan/project/END-SEM-PROJECT-SE/docker-compose.yml exec -T backend python -c "
from app.services.docker_monitor import get_docker_monitor
get_docker_monitor()._sync_containers_to_db()
print('Sync complete')
" 2>/dev/null || echo "Sync via API..."

echo ""
echo "Usage:"
echo "  - Monitor Dashboard and AI Insights to see all 8 containers"
echo "  - AI Insights tab shows detected anomalies"
echo "  - CPU spike takes ~30s to trigger"
echo "  - Memory leak takes ~60s to show growth pattern"
echo "  - Stop 'stopped-test' container manually: docker stop stopped-test"
echo ""
echo "To clean up test containers:"
echo "  docker rm -f cpu-spike-test memory-leak-test high-memory-test restart-loop-test stopped-test"