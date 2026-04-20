# API Documentation

## Base URL

```
http://localhost:8000/api
```

## Authentication

All authenticated endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

## Endpoints

### Health Check

**GET** `/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00"
}
```

---

### Authentication

**POST** `/auth/token`

Login to get JWT token.

**Request Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "requires_2fa": false,
  "user_id": 1
}
```

**Rate Limit:** 10 requests/minute

---

### 2FA Setup

**POST** `/auth/2fa/setup`

Setup TOTP-based 2FA authentication.

**Request Body:**
```json
{
  "user_id": 1,
  "code": "JBSWY3DPEHPK3PXP"
}
```

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,..."
}
```

---

### 2FA Verify

**POST** `/auth/2fa/verify`

Verify 2FA code and get token.

**Request Body:**
```json
{
  "user_id": 1,
  "code": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

---

### 2FA Disable

**POST** `/auth/2fa/disable`

Disable 2FA for a user.

**Request Body:**
```json
{
  "user_id": 1,
  "code": "123456",
  "password": "admin123"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "2FA disabled"
}
```

---

### Logout All Devices

**POST** `/auth/logout-all`

Invalidate all sessions by changing password.

**Request Body:**
```json
{
  "new_password": "new_secure_password"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "All sessions invalidated. Please login with new password."
}
```

---

### Containers

**GET** `/containers`

List all containers.

**Response:**
```json
[
  {
    "id": "abc123...",
    "name": "nginx",
    "image": "nginx:latest",
    "status": "running",
    "created_at": "2024-01-01T00:00:00",
    "last_updated": "2024-01-01T00:00:00"
  }
]
```

---

**GET** `/containers/{container_id}`

Get container details with metrics and alerts.

**Response:**
```json
{
  "id": "abc123...",
  "name": "nginx",
  "image": "nginx:latest",
  "status": "running",
  "metrics": [...],
  "alerts": [...]
}
```

---

**GET** `/containers/{container_id}/metrics`

Get container metrics history.

**Query Parameters:**
- `limit` (int, default: 100)

**Response:**
```json
{
  "container_id": "abc123...",
  "metrics": [
    {
      "id": 1,
      "cpu_percent": 25.5,
      "memory_percent": 40.2,
      "memory_usage": 524288000,
      "timestamp": "2024-01-01T00:00:00"
    }
  ]
}
```

---

**GET** `/containers/{container_id}/logs`

Get container logs.

**Query Parameters:**
- `lines` (int, default: 100)

**Response:**
```json
{
  "container_id": "abc123...",
  "logs": "2024/01/01 00:00:00 [notice] ..."
}
```

---

**POST** `/containers/{container_id}/restart`

Restart a container.

**Response:**
```json
{
  "status": "success",
  "message": "Container abc123... restarted"
}
```

**Rate Limit:** 30 requests/minute

---

**POST** `/containers/{container_id}/pause`

Pause a container.

---

**POST** `/containers/{container_id}/unpause`

Unpause a container.

---

**POST** `/containers`

Create a new container.

**Request Body:**
```json
{
  "image": "nginx:latest",
  "name": "my-container",
  "ports": { "80": "8080" },
  "environment": { "NODE_ENV": "production" },
  "memory_limit": 512000000,
  "cpu_limit": 0.5
}
```

**Response:**
```json
{
  "status": "success",
  "container": {
    "id": "abc123...",
    "name": "my-container",
    "image": "nginx:latest",
    "status": "created"
  }
}
```

**Rate Limit:** 20 requests/minute

---

### Metrics

**GET** `/metrics/history`

Get metrics history across all containers or filtered.

**Query Parameters:**
- `container_id` (string, optional)
- `hours` (int, default: 24)

**Response:**
```json
{
  "metrics": [
    {
      "container_id": "abc123...",
      "cpu_percent": 25.5,
      "memory_percent": 40.2,
      "memory_usage": 524288000,
      "timestamp": "2024-01-01T00:00:00"
    }
  ]
}
```

**Rate Limit:** 30 requests/minute

---

**GET** `/containers?favorites=true`

List favorite containers only.

**Query Parameters:**
- `favorites` (bool)

---

**POST** `/containers/bulk/start`

Start multiple containers.

**Request Body:**
```json
{
  "container_ids": ["abc123", "def456"]
}
```

**Response:**
```json
{
  "status": "success",
  "results": [
    { "id": "abc123", "success": true },
    { "id": "def456", "success": false }
  ]
}
```

---

**POST** `/containers/bulk/stop`

Stop multiple containers.

**Request Body:**
```json
{
  "container_ids": ["abc123", "def456"]
}
```

---

**POST** `/containers/bulk/restart`

Restart multiple containers.

**Request Body:**
```json
{
  "container_ids": ["abc123", "def456"]
}
```

---

**POST** `/containers/bulk/delete`

Delete multiple containers (admin only).

**Request Body:**
```json
{
  "container_ids": ["abc123", "def456"]
}
```

---

**POST** `/containers/{container_id}/stop`

Stop a container.

**Rate Limit:** 30 requests/minute

---

**PUT** `/containers/{container_id}`

Update container metadata.

**Request Body:**
```json
{
  "group": "production",
  "is_favorite": true
}
```

**Response:**
```json
{
  "id": "abc...",
  "name": "nginx",
  "group": "production",
  "is_favorite": true
}
```

---

**PUT** `/containers/{container_id}/env`

Update environment variables.

**Request Body:**
```json
{
  "NODE_ENV": "production",
  "DEBUG": "false"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Environment updated"
}
```

---

**PUT** `/containers/{container_id}/ports`

Update port mappings.

**Request Body:**
```json
{
  "80": 8080
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Ports updated"
}
```

---

**GET** `/containers/group/{group}`

List containers by group.

**Response:**
```json
[
  { "id": "abc...", "name": "web", "group": "production" }
]
```

---

**POST** `/containers/{container_id}/exec`

Execute command in container.

**Request Body:**
```json
{
  "cmd": ["ls", "-la"],
  "tty": true,
  "stdin": false
}
```

**Response:**
```json
{
  "exec_id": "exec_session_abc",
  "container_id": "abc..."
}
```

---

### Alerts

**GET** `/alerts`

Get alert history.

**Query Parameters:**
- `limit` (int, default: 50)
- `container_id` (string, optional)

**Response:**
```json
[
  {
    "id": 1,
    "container_id": "abc123...",
    "alert_type": "cpu_high",
    "message": "CPU usage above threshold",
    "severity": "warning",
    "timestamp": "2024-01-01T00:00:00"
  }
]
```

---

### Stacks

**GET** `/stacks`

List all deployed stacks.

**Response:**
```json
[
  {
    "id": 1,
    "name": "my-stack",
    "compose_file": "version: '3'...",
    "status": "running",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

---

**POST** `/stacks`

Deploy a new stack.

**Request Body:**
```json
{
  "name": "my-stack",
  "compose_file": "version: '3'\nservices:\n  web:\n    image: nginx"
}
```

**Rate Limit:** 10 requests/minute

---

**POST** `/stacks/{stack_id}/start`

Start a stack.

**Rate Limit:** 20 requests/minute

---

**POST** `/stacks/{stack_id}/stop`

Stop a stack.

**Rate Limit:** 20 requests/minute

---

**DELETE** `/stacks/{stack_id}`

Delete a stack.

---

### Hosts

**GET** `/hosts`

List all Docker hosts.

**Response:**
```json
[
  {
    "id": 1,
    "name": "local",
    "socket_path": "/var/run/docker.sock",
    "api_version": "1.41",
    "status": "connected",
    "last_seen": "2024-01-01T00:00:00"
  }
]
```

---

**POST** `/hosts`

Add a new Docker host.

**Request Body:**
```json
{
  "name": "remote-server",
  "socket_path": "unix:///var/run/docker.sock",
  "api_version": "1.41"
}
```

**Rate Limit:** 10 requests/minute

---

**POST** `/hosts/{host_id}/test`

Test host connection.

**Rate Limit:** 20 requests/minute

---

**POST** `/hosts/{host_id}/activate`

Activate a Docker host (switch current connection).

**Rate Limit:** 10 requests/minute

---

**DELETE** `/hosts/{host_id}`

Remove a host.

---

### Settings

**GET** `/settings`

Get current settings.

**Response:**
```json
{
  "poll_interval": 5,
  "cpu_threshold": 90,
  "memory_threshold": 90,
  "metrics_ttl_days": 7,
  "recovery_enabled": true,
  "jwt_expiration_hours": 24
}
```

---

**PUT** `/settings`

Update settings.

**Request Body:**
```json
{
  "poll_interval": 10,
  "cpu_threshold": 80,
  "memory_threshold": 85
}
```

**Rate Limit:** 10 requests/minute

---

### Users

**GET** `/users`

List all users (admin only).

**Response:**
```json
[
  { "id": 1, "username": "admin", "role": "admin", "created_at": "2024-01-01T00:00:00", "must_change_password": false }
]
```

---

**POST** `/users`

Create new user (admin only).

**Request Body:**
```json
{
  "username": "newuser",
  "password": "password123",
  "role": "user"
}
```

---

**PUT** `/users/{user_id}`

Update user (admin only).

**Request Body:**
```json
{
  "password": "newpassword",
  "role": "admin",
  "force_password_change": true
}
```

---

**DELETE** `/users/{user_id}`

Delete user (admin only).

---

### Alert Rules

**GET** `/alert-rules`

List alert rules.

**Query Parameters:**
- `container_id` (string, optional)

**Response:**
```json
[
  {
    "id": 1,
    "container_id": "abc...",
    "name": "High CPU Alert",
    "cpu_threshold": 80,
    "memory_threshold": 80,
    "enabled": true
  }
]
```

---

**POST** `/alert-rules`

Create alert rule.

**Request Body:**
```json
{
  "name": "High CPU Alert",
  "cpu_threshold": 80,
  "memory_threshold": 80,
  "container_id": "abc...",
  "enabled": true
}
```

---

**PUT** `/alert-rules/{rule_id}`

Update alert rule.

---

**DELETE** `/alert-rules/{rule_id}`

Delete alert rule.

---

### Schedules

**GET** `/schedules`

List scheduled actions.

**Query Parameters:**
- `container_id` (string, optional)

**Response:**
```json
[
  {
    "id": 1,
    "container_id": "abc...",
    "container_name": "nginx",
    "action": "restart",
    "time": "03:00",
    "enabled": true
  }
]
```

---

**POST** `/schedules`

Create scheduled action.

**Request Body:**
```json
{
  "container_id": "abc...",
  "action": "restart",
  "time": "03:00"
}
```

---

**PUT** `/schedules/{schedule_id}`

Update scheduled action.

**Request Body:**
```json
{
  "action": "stop",
  "time": "04:00",
  "enabled": false
}
```

---

**DELETE** `/schedules/{schedule_id}`

Delete scheduled action.

---

### Backup

**GET** `/backup/list`

List available backups.

**Response:**
```json
{
  "backups": [
    {
      "filename": "dockwatch_backup_20240101.tar.gz",
      "size": 1234567,
      "created": "2024-01-01T00:00:00"
    }
  ]
}
```

---

**POST** `/backup/create`

Create new backup.

**Query Parameters:**
- `include_metrics` (bool, default: true)

**Response:**
```json
{
  "status": "pending",
  "message": "Backup creation started",
  "filename": "dockwatch_backup_20240101.tar.gz"
}
```

---

**POST** `/backup/restore`

Restore from backup.

**Request Body:** multipart file upload (.tar.gz)

**Response:**
```json
{
  "status": "success",
  "message": "Backup restored successfully",
  "restored": {
    "containers": 5,
    "stacks": 2,
    "hosts": 1
  }
}
```

---

### Audit

**GET** `/audit/logs`

Get audit logs.

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 50)
- `action` (string, optional)
- `resource_type` (string, optional)
- `user_id` (int, optional)
- `days` (int, default: 7)

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 1,
      "action": "container_restart",
      "resource_type": "container",
      "resource_id": "abc...",
      "ip_address": "192.168.1.1",
      "timestamp": "2024-01-01T00:00:00"
    }
  ],
  "total": 100,
  "skip": 0,
  "limit": 50
}
```

---

**GET** `/audit/stats`

Get audit statistics.

**Response:**
```json
{
  "period_days": 7,
  "total_actions": 50,
  "actions_by_type": { "container_restart": 10 },
  "resources_by_type": { "container": 30 },
  "daily_activity": [
    { "date": "2024-01-01", "count": 5 }
  ]
}
```

---

## WebSocket API

**Endpoint:** `/ws/metrics`

**Connection:** Requires JWT token in auth object.

**Events:**

| Event | Payload | Description |
|-------|---------|-------------|
| `connect` | - | Connected to WebSocket |
| `pong` | - | Response to heartbeat |
| `metrics` | `{ metrics: [...] }` | Real-time metrics |
| `container_update` | `{ container: {...} }` | Container state changed |
| `alert` | `{ ...alert }` | New alert triggered |

**Client Events:**

| Event | Description |
|-------|-------------|
| `ping` | Send heartbeat |

---

## Error Responses

**401 Unauthorized**
```json
{
  "detail": "Incorrect username or password"
}
```

**404 Not Found**
```json
{
  "detail": "Container not found"
}
```

**429 Rate Limited**
```json
{
  "detail": "Rate limit exceeded: 60 per minute",
  "retry_after": "60 per minute"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Failed to restart container"
}
```