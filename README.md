# DockWatch Documentation

Welcome to DockWatch, a real-time Docker container monitoring and management dashboard with AI analytics, auto-recovery, cost optimization, and security features.

## Overview

DockWatch provides real-time monitoring, auto-recovery, and management for Docker containers.

## Key Features

| Feature | Description |
|---------|-------------|
| Real-time Monitoring | Live CPU, memory, network stats |
| AI Analytics | Anomaly detection and root cause analysis |
| Cost Optimization | Resource waste detection and savings |
| Auto-Recovery | Automatic container restart on failure |
| CVE Scanning | Trivy-based security vulnerability detection |
| 3D Visualization | Three.js cluster topology |
| CSV/JSON Export | Export metrics data |

## Quick Start
```bash
./start.sh
```

## Access
- **Dashboard**: http://localhost:3001
- **API**: http://localhost:3001/api
- **Health**: http://localhost:3001/api/health

## Default Credentials
- **Username**: `admin`
- **Password**: `admin123` (development only)

## New API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/metrics/summary` | Resource usage + waste analysis |
| `/api/metrics/export` | CSV/JSON metrics export |
| `/api/containers?search=` | Live container search |
| `/api/ai/analyze/:id` | AI-powered container analysis |
| `/api/trivy/scan/:id` | CVE vulnerability scanning |
| `/api/trivy/health` | Trivy availability check |

## Navigation

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Container fleet overview + cost metrics |
| `/topology` | Topology | 3D cluster visualization |
| `/security` | Security | CVE vulnerability scanner |
| `/ai` | AI Insights | Anomaly detection & analysis |
| `/notifications` | Notifications | Webhook configuration |

## Webhook Configuration

Set these environment variables for Slack/Teams/PagerDuty:

```bash
# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ

# Microsoft Teams
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/XXX

# PagerDuty
PAGERDUTY_KEY=your-pagerduty-integration-key
```

Endpoints:
- `POST /api/webhooks/test` - Send test notification
- `GET /api/webhooks/status` - Check webhook configuration

## Guides
- [Getting Started](/docs/GETTING-STARTED.md)
- [API Reference](/docs/API.md)
- [Deployment](/docs/DEPLOYMENT.md)
