# 🟡 Important Issues - Should Fix for Production

## IMP-001: Add Frontend Tests
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned  
**Estimated Effort:** 3-4 days

**Description:**
Add unit and integration tests for frontend components.

**Tasks:**
- [ ] Set up Vitest testing framework
- [ ] Add tests for API service
- [ ] Add tests for components (ContainerCard, MetricsChart, etc.)
- [ ] Add tests for pages
- [ ] Set up test coverage reporting

**Acceptance Criteria:**
- Minimum 70% code coverage
- All critical paths tested
- Tests run in CI/CD

**Files:**
- `/frontend/vitest.config.ts` (new)
- `/frontend/src/**/*.test.ts` (new)

---

## IMP-002: Add Backend Tests
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned  
**Estimated Effort:** 4-5 days

**Description:**
Add unit and integration tests for backend API.

**Tasks:**
- [ ] Set up pytest with fixtures
- [ ] Add tests for API endpoints
- [ ] Add tests for services (docker_monitor, cleanup_service)
- [ ] Add tests for database models
- [ ] Add integration tests with test database
- [ ] Set up test coverage reporting

**Acceptance Criteria:**
- Minimum 80% code coverage for backend
- All API endpoints have tests
- Database operations tested
- Tests run in CI/CD

**Files:**
- `/backend/pytest.ini` (new)
- `/backend/tests/` (new directory)
- `/backend/tests/conftest.py` (new)
- `/backend/tests/test_*.py` (new)

---

## IMP-003: Add API Documentation
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned  
**Estimated Effort:** 2-3 days

**Description:**
Add comprehensive API documentation with Swagger/OpenAPI.

**Tasks:**
- [ ] Add detailed docstrings to all endpoints
- [ ] Add request/response examples
- [ ] Document authentication methods
- [ ] Add error response documentation
- [ ] Create API usage guide

**Acceptance Criteria:**
- All endpoints documented in Swagger UI
- Examples provided for complex requests
- Authentication documented
- Error codes explained

**Files:**
- `/backend/app/api/*.py` (add docstrings)
- `/docs/api/README.md` (new)

---

## IMP-004: Add Health Check Endpoint
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned  
**Estimated Effort:** 1 day

**Description:**
Add a health check endpoint for monitoring and load balancers.

**Tasks:**
- [ ] Create `/health` endpoint
- [ ] Check database connectivity
- [ ] Check Docker connectivity
- [ ] Return appropriate status codes (200 for healthy, 503 for unhealthy)

**Acceptance Criteria:**
- `/health` returns 200 when all services healthy
- `/health` returns 503 when services down
- Response includes status of each component

**Files:**
- `/backend/app/api/health.py` (new)
- `/backend/app/main.py` (add router)

---

## IMP-005: Add Frontend Error Handling
**Priority:** Important  
**Status:** 🟡 To Do  
**Assignee:** Unassigned  
**Estimated Effort:** 2 days

**Description:**
Add comprehensive error handling and user feedback in frontend.

**Tasks:**
- [ ] Add toast notifications for success/error messages
- [ ] Add loading states for all async operations
- [ ] Add retry logic for failed requests
- [ ] Add offline detection

**Acceptance Criteria:**
- Users see clear error messages
- Loading states prevent double-submissions
- Failed requests can be retried
- Offline state is detected and shown

**Files:**
- `/frontend/src/components/Toast.tsx` (new)
- `/frontend/src/hooks/useToast.ts` (new)
- `/frontend/src/hooks/useOffline.ts` (new)

---

## Summary

These important issues should be addressed after the critical issues are fixed. They will make the application more robust, maintainable, and user-friendly. Focus on testing and documentation before adding new features.