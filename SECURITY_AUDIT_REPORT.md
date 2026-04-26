# Security Audit Report - DockWatch
**Date:** 2026-04-25

## Critical Fixes Applied

### 1. JWT Authentication (HIGH)
- **Before:** Symmetric HS256 with dev secret, 24h expiry, no refresh tokens
- **After:** 
  - RSA asymmetric keys (RS256) with auto-generation
  - Access token: 1 hour expiry, Refresh token: 7 days
  - Token revocation via blacklist
  - Token type validation (access vs refresh)
  - Fresh token flag for sensitive operations
  - Key rotation support

### 2. WebSocket Authentication (CRITICAL)
- **Before:** No authentication on any WebSocket endpoint
- **After:**
  - All endpoints require JWT token via query parameter
  - Admin-only enforcement on exec endpoint
  - Token validation before connection acceptance
  - Proper error handling with close codes

### 3. Password Security (HIGH)
- **Before:** bcrypt default cost, no policy, admin/admin123 default
- **After:**
  - bcrypt cost factor 14
  - Force password change on first login (must_change_password flag)
  - Password complexity: 12+ chars, uppercase, lowercase, digit, special
  - Separate force-change endpoint
  - Token revocation on password change

### 4. File Permissions (MEDIUM)
- **Before:** SQLite DB created with 0o666 (world-readable)
- **After:** 
  - Database file: 0o600 (owner read/write only)
  - Database directory: 0o700
  - Foreign key constraints enabled
  - WAL mode for concurrency

### 5. Audit Log Integrity (MEDIUM)
- **Before:** No tamper protection
- **After:**
  - SHA-256 hash chain for each log entry
  - Each entry includes previous hash
  - Verifiable integrity chain
  - Separate hash_chain column

### 6. Rate Limiting (MEDIUM)
- **Before:** Only some endpoints rate-limited
- **After:**
  - All endpoints have appropriate rate limits
  - GET: 60/min, POST/PUT/DELETE: 30/min
  - Sensitive endpoints (auth): 10/min
  - Consistent across all routes

### 7. Security Headers (MEDIUM)
- **Added:**
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Content-Security-Policy
  - Strict-Transport-Security
  - Referrer-Policy: strict-origin-when-cross-origin

### 8. Input Validation (MEDIUM)
- **Enhanced:**
  - All rate-limited endpoints have Request parameter
  - Container ID, name, image validation
  - Positive integer validation
  - JSON object validation

## Security Headers Middleware
- Applied to all responses
- CSP restricts to same-origin
- HSTS enforces HTTPS
- Frame options prevent clickjacking

## Authorization
- Role-based access control (user/admin)
- Admin-only exec endpoint
- Token type enforcement
- Owner checks needed (future - requires user_id FK)

## Outstanding Issues

### Critical (Requires Immediate Action)
1. Docker socket exposure - requires Docker-in-Docker or API proxy
2. No encryption at rest for database
3. No encryption for TOTP secrets
4. Missing user-container ownership model
5. No HTTPS/TLS termination in app

### High Priority
1. Implement Redis for token blacklist (persistence)
2. Secrets management (Vault/AWS Secrets Manager)
3. Backup encryption
4. Container resource limits (CPU/memory)
5. Non-privileged container execution

### Medium Priority
1. Password breach checking (HaveIBeenPwned API)
2. Account lockout after failed attempts
3. Session management with idle timeout
4. Regular security scanning (SAST/DAST)
5. Audit log export/retention policy
6. Key rotation schedule
7. 2FA backup codes

### Low Priority
1. CSP nonce for inline scripts
2. Advanced rate limiting (IP-based)
3. Anomaly detection
4. Security event alerting
5. Penetration testing

## Compliance
- GDPR: PII handling, right to erasure
- Audit trails: Comprehensive logging
- Data retention: TTL on metrics
- Access control: Role-based

## Deployment Recommendations

1. Set DOCKWATCH_JWT_SECRET (64+ chars) in production
2. Use TLS reverse proxy (nginx/Caddy)
3. Run as non-root user
4. Mount Docker socket read-only if needed
5. Use secrets management (never in code)
6. Enable automatic security updates
7. Monitor logs for suspicious activity
8. Regular backups with encryption
9. Network isolation (firewall rules)
10. Rate limiting at edge (Cloudflare)

## Testing
All existing tests pass with new security features.

## Files Modified
- backend/app/core/security.py - RSA keys, refresh tokens, token revocation
- backend/app/api/endpoints.py - Rate limiting, password change, refresh
- backend/app/api/audit.py - Hash chain integrity
- backend/app/api/websocket.py - Authentication on all endpoints
- backend/app/db/models.py - FK constraints, file permissions, hash_chain
- backend/app/main.py - Security headers, exception handlers
- backend/app/models/schemas.py - Token response with refresh
- backend/tests/test_auth.py - Updated for 403 status

