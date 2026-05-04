# Plan: Ownership Model Implementation

Implement resource-level ownership across all Docker-related features to prevent unauthorized access.

## Objective
- Restrict access to Containers, Stacks, Images, Volumes, and Networks based on user ownership.
- Admin users retain full access.

## Key Files & Context
- `backend/app/db/models.py`: Database models.
- `backend/app/api/endpoints.py`: Main API endpoints (Containers, Stacks).
- `backend/app/api/docker_resources.py`: Docker resource endpoints (Images, Volumes, Networks).
- `backend/app/api/websocket.py`: WebSocket streams (Logs, Exec).

## Implementation Steps

### 1. Database Schema Updates
- **Stack Model**: Add `user_id` column (Integer, ForeignKey).
- **DockerResource Model**: Create new table to track ownership of Images, Volumes, and Networks.
  - `id`: Integer PK
  - `resource_type`: String (image, volume, network)
  - `resource_id`: String (Docker ID or name)
  - `user_id`: Integer FK
- **Migrations**: Generate and run alembic migration.

### 2. Service Layer Helpers
- Update `check_container_ownership` in `endpoints.py` if needed.
- Implement `check_resource_ownership(db, resource_type, resource_id, current_user)` helper.

### 3. API Enforcement
- **Stacks API**:
  - `GET /stacks`: Filter by `user_id` for non-admins.
  - `POST /stacks`: Set `user_id` on creation.
  - `GET/POST/DELETE /stacks/{id}`: Verify ownership.
- **Docker Resources API**:
  - `POST /docker/images/pull`: Record ownership in `DockerResource`.
  - `POST /docker/volumes`: Record ownership in `DockerResource`.
  - `POST /docker/networks`: Record ownership in `DockerResource`.
  - `DELETE /docker/*`: Verify ownership before removal.
- **WebSocket API**:
  - `GET /ws/logs/{container_id}`: Verify container ownership before streaming.

### 4. Fix Inconsistencies
- Ensure `bulk_container_operation` and other batch actions consistently use ownership checks.

## Verification & Testing
- **Unit Tests**:
  - Test unauthorized access to other users' stacks.
  - Test unauthorized deletion of images/volumes.
  - Test admin bypass of ownership checks.
- **Manual Verification**:
  - Create resources as User A, try to delete as User B.
