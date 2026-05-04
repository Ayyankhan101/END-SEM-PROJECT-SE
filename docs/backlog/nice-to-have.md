# 🟢 Nice to Have - Future Enhancements

## NTH-001: Add Container Terminal Access
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned  
**Estimated Effort:** 5-7 days

**Description:**
Add web-based terminal access to containers for debugging and management.

**Tasks:**
- [ ] Add WebSocket endpoint for terminal
- [ ] Integrate xterm.js in frontend
- [ ] Handle container exec with PTY
- [ ] Add authentication for terminal access
- [ ] Add session management

**Acceptance Criteria:**
- Users can open terminal for any running container
- Terminal supports full PTY features
- Sessions are secure and authenticated
- Multiple terminals can be open simultaneously

**Files:**
- `/backend/app/api/terminal.py` (new)
- `/frontend/src/components/Terminal.tsx` (new)
- `/frontend/src/pages/ContainerTerminal.tsx` (new)

---

## NTH-002: Add Container File Manager
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned  
**Estimated Effort:** 4-5 days

**Description:**
Add web-based file manager for container filesystems.

**Tasks:**
- [ ] Add API endpoints for file operations
- [ ] Create file browser UI
- [ ] Support file upload/download
- [ ] Add file editing capabilities
- [ ] Add directory navigation

**Acceptance Criteria:**
- Users can browse container filesystem
- Files can be uploaded/downloaded
- Text files can be edited in browser
- Directory operations work (create, delete, rename)

**Files:**
- `/backend/app/api/files.py` (new)
- `/frontend/src/components/FileManager.tsx` (new)
- `/frontend/src/pages/ContainerFiles.tsx` (new)

---

## NTH-003: Add Multi-Host Support
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned  
**Estimated Effort:** 7-10 days

**Description:**
Fully implement multi-host Docker management.

**Tasks:**
- [ ] Add host management UI
- [ ] Implement host switching
- [ ] Aggregate metrics across hosts
- [ ] Add host health monitoring
- [ ] Support remote Docker hosts via TLS

**Acceptance Criteria:**
- Multiple Docker hosts can be managed
- Users can switch between hosts
- Dashboard shows aggregated data from all hosts
- Host connectivity is monitored
- Remote hosts work securely

**Files:**
- `/frontend/src/pages/Hosts.tsx` (enhance)
- `/backend/app/services/multi_host.py` (new)

---

## NTH-004: Add RBAC (Role-Based Access Control)
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned  
**Estimated Effort:** 5-7 days

**Description:**
Add role-based access control for multi-user environments.

**Tasks:**
- [ ] Add roles table to database
- [ ] Add permissions system
- [ ] Implement role checks in API
- [ ] Add role management UI
- [ ] Add default roles (admin, operator, viewer)

**Acceptance Criteria:**
- Users can have different roles
- API endpoints check permissions
- UI adapts to user role
- Roles can be managed by admins

**Files:**
- `/backend/app/db/models.py` (add Role model)
- `/backend/app/core/rbac.py` (new)
- `/frontend/src/hooks/usePermissions.ts` (new)

---

## NTH-005: Add Dark/Light Theme Toggle
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned  
**Estimated Effort:** 2-3 days

**Description:**
Add ability to toggle between dark and light themes.

**Tasks:**
- [ ] Create light theme color palette
- [ ] Add theme context/provider
- [ ] Add theme toggle button
- [ ] Persist theme preference
- [ ] Update all components to use theme

**Acceptance Criteria:**
- Users can toggle between dark/light themes
- Theme preference is saved
- All components respect the theme
- Transition between themes is smooth

**Files:**
- `/frontend/src/contexts/ThemeContext.tsx` (new)
- `/frontend/src/hooks/useTheme.ts` (new)

---

## NTH-006: Add Container Templates
**Priority:** Nice to Have  
**Status:** 🟢 Backlog  
**Assignee:** Unassigned  
**Estimated Effort:** 3-4 days

**Description:**
Add pre-defined container templates for common services.

**Tasks:**
- [ ] Create templates database table
- [ ] Add common templates (nginx, postgres, redis, etc.)
- [ ] Add template selection UI
- [ ] Allow custom templates
- [ ] Import/export templates

**Acceptance Criteria:**
- Users can deploy from templates
- Common services have pre-configured templates
- Custom templates can be saved
- Templates can be shared

**Files:**
- `/backend/app/db/models.py` (add Template model)
- `/frontend/src/pages/Templates.tsx` (new)

---

## Summary

These are all future enhancements that would make DockWatch more feature-rich but aren't required for the core functionality. Focus on the critical and important issues first, then tackle these based on user feedback and priorities.

The most valuable nice-to-have features would be:
1. **Terminal Access** - Very useful for debugging
2. **File Manager** - Helpful for quick edits
3. **Container Templates** - Speeds up deployments