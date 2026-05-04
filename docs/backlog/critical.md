# 🔴 Critical Issues - Must Fix Before Production

## Database & Models

### DB-001: Consolidate Database Models
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Consolidate `models.py` and `database.py` into one file. Currently both define the same models causing confusion and potential conflicts.

**Tasks:**
- [ ] Merge `database.py` into `models.py`
- [ ] Update all imports across the codebase
- [ ] Test database initialization

**Files:**
- `/backend/app/db/models.py`
- `/backend/app/db/database.py`
- `/backend/app/db/__init__.py`

---

### DB-002: Update Database Package Exports
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Update `app/db/__init__.py` to export all models including new ones (AuditLog, NotificationChannel, NotificationLog).

**Tasks:**
- [ ] Add exports for all models
- [ ] Add exports for helper functions (get_db, init_db, get_session)
- [ ] Verify imports work across the project

**Files:**
- `/backend/app/db/__init__.py`

---

### DB-003: Add Missing Settings Model
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Add `Settings` SQLAlchemy model to store application settings in database. Currently `backup.py` imports `Settings` which doesn't exist as a model.

**Tasks:**
- [ ] Create Settings model in models.py
- [ ] Add settings table fields (key, value, updated_at)
- [ ] Update backup.py to use the model
- [ ] Create migration for the new table

**Files:**
- `/backend/app/db/models.py`
- `/backend/app/api/backup.py`

---

### DB-004: Create Alembic Migrations for New Models
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Create database migrations for new models: AuditLog, NotificationChannel, NotificationLog, and Settings.

**Tasks:**
- [ ] Generate migration with `alembic revision --autogenerate`
- [ ] Review migration script
- [ ] Test migration upgrade/downgrade
- [ ] Document migration process

**Files:**
- `/backend/alembic/versions/`

---

## API Issues

### API-001: Fix Docker Resources API Client Usage
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Fix `DockerClientService.get_client()` usage in `docker_resources.py`. The service doesn't have this class method.

**Tasks:**
- [ ] Change to use `get_docker_client_service()` function
- [ ] Update all endpoints in docker_resources.py
- [ ] Test image/volume/network operations

**Files:**
- `/backend/app/api/docker_resources.py`

---

### API-002: Fix Backup API Config Reference
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Fix `app_settings.CONFIG_PATH` reference in `backup.py`. The config module uses `get_config()` function, not a settings object.

**Tasks:**
- [ ] Update import to use `get_config()`
- [ ] Fix CONFIG_PATH reference
- [ ] Test backup functionality

**Files:**
- `/backend/app/api/backup.py`

---

### API-003: Add Rate Limiting to New Endpoints
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Add rate limiting to resource-intensive endpoints: image pull, backup/restore, audit log queries.

**Tasks:**
- [ ] Add rate limiting to docker_resources.py endpoints
- [ ] Add rate limiting to backup.py endpoints
- [ ] Add rate limiting to audit.py endpoints
- [ ] Test rate limiting works

**Files:**
- `/backend/app/api/docker_resources.py`
- `/backend/app/api/backup.py`
- `/backend/app/api/audit.py`

---

## Frontend Issues

### FE-001: Add Missing API Methods
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Add all new backend endpoint methods to frontend `api.ts`.

**Tasks:**
- [ ] Add audit API methods (getAuditLogs, getAuditStats)
- [ ] Add notification API methods (getChannels, createChannel, etc.)
- [ ] Add backup API methods (listBackups, createBackup, restoreBackup)
- [ ] Add Docker resources API methods (getImages, getVolumes, getNetworks, etc.)

**Files:**
- `/frontend/src/services/api.ts`

---

### FE-002: Add Missing Type Definitions
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Add TypeScript types for all new backend models.

**Tasks:**
- [ ] Add AuditLog type
- [ ] Add NotificationChannel and NotificationLog types
- [ ] Add DockerImage, DockerVolume, DockerNetwork types
- [ ] Add BackupInfo type

**Files:**
- `/frontend/src/types/index.ts`

---

### FE-003: Create Missing Frontend Pages
**Priority:** Critical  
**Status:** 🔴 To Do  
**Assignee:** Unassigned

**Description:**
Create frontend pages for new backend features.

**Tasks:**
- [ ] Create AuditLogs.tsx page
- [ ] Create Notifications.tsx page for channel management
- [ ] Create Backup.tsx page for backup/restore
- [ ] Create DockerResources.tsx page for images/volumes/networks
- [ ] Add routes to App.tsx

**Files:**
- `/frontend/src/pages/AuditLogs.tsx` (new)
- `/frontend/src/pages/Notifications.tsx` (new)
- `/frontend/src/pages/Backup.tsx` (new)
- `/frontend/src/pages/DockerResources.tsx` (new)
- `/frontend/src/App.tsx` (update routes)

---

## 🟡 Important Issues (Should Fix)

### IMP-001: Add Frontend Tests
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned

**Description:**
Add unit and integration tests for frontend components.

**Tasks:**
- [ ] Set up Vitest testing framework
- [ ] Add tests for API service
- [ ] Add tests for components
- [ ] Add tests for pages

**Files:**
- `/frontend/src/**/*.test.ts` (new)

---

### IMP-002: Add Backend Tests
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned

**Description:**
Add unit and integration tests for backend API.

**Tasks:**
- [ ] Set up pytest
- [ ] Add tests for API endpoints
- [ ] Add tests for services
- [ ] Add tests for database models

**Files:**
- `/backend/tests/` (new)

---

### IMP-003: Add API Documentation
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned

**Description:**
Add comprehensive API documentation.

**Tasks:**
- [ ] Add docstrings to all endpoints
- [ ] Set up Swagger/OpenAPI documentation
- [ ] Add example requests/responses
- [ ] Document authentication

**Files:**
- `/backend/app/api/*.py` (add docstrings)

---

### IMP-004: Add Health Check Endpoint
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned

**Description:**
Add a health check endpoint for monitoring and load balancers.

**Tasks:**
- [ ] Create `/health` endpoint
- [ ] Check database connectivity
- [ ] Check Docker connectivity
- [ ] Return appropriate status codes

**Files:**
- `/backend/app/api/health.py` (new)

---

## 🟢 Nice to Have (Future Enhancements)

### NTH-001: Add Container Terminal Access
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned

**Description:**
Add web-based terminal access to containers.

**Tasks:**
- [ ] Add WebSocket endpoint for terminal
- [ ] Integrate xterm.js in frontend
- [ ] Handle container exec

---

### NTH-002: Add Container File Manager
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned

**Description:**
Add web-based file manager for container filesystems.

**Tasks:**
- [ ] Add API endpoints for file operations
- [ ] Create file browser UI
- [ ] Support upload/download

---

### NTH-003: Add Multi-Host Support
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned

**Description:**
Fully implement multi-host Docker management.

**Tasks:**
- [ ] Add host management UI
- [ ] Implement host switching
- [ ] Aggregate metrics across hosts

---

### NTH-004: Add RBAC (Role-Based Access Control)
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned

**Description:**
Add role-based access control for multi-user environments.

**Tasks:**
- [ ] Add roles table
- [ ] Add permissions system
- [ ] Implement role checks in API

---

## Summary

To make DockWatch production-ready, focus on this order:

1. **Week 1**: Fix critical database issues (models consolidation, Settings model, migrations)
2. **Week 2**: Fix API issues (Docker client, rate limiting, config references)
3. **Week 3**: Complete frontend (API methods, types, missing pages)
4. **Week 4**: Testing and documentation

The critical issues will prevent the app from running at all, so those must be fixed first. The important issues will make the app usable and maintainable. The nice-to-have items can be added later as enhancements.