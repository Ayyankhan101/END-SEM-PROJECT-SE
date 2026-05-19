"""
WB-09: White box tests for audit log endpoint and hash chain.
Tests CRUD access control, filtering, and compute_audit_hash logic.
"""
import pytest
import hashlib
from app.core.security import create_access_token
from app.api.audit import compute_audit_hash


def admin_headers():
    token = create_access_token({"sub": "admin", "role": "admin", "user_id": 1})
    return {"Authorization": f"Bearer {token}"}


def viewer_headers():
    token = create_access_token({"sub": "viewer", "role": "viewer", "user_id": 99})
    return {"Authorization": f"Bearer {token}"}


# ─── WB-09: compute_audit_hash unit tests ────────────────────────────────────

class TestComputeAuditHash:
    def test_hash_deterministic(self):
        h1 = compute_audit_hash("data", "prev")
        h2 = compute_audit_hash("data", "prev")
        assert h1 == h2

    def test_hash_changes_with_different_data(self):
        h1 = compute_audit_hash("data_a", "prev")
        h2 = compute_audit_hash("data_b", "prev")
        assert h1 != h2

    def test_hash_changes_with_different_prev(self):
        h1 = compute_audit_hash("data", "prev_a")
        h2 = compute_audit_hash("data", "prev_b")
        assert h1 != h2

    def test_hash_no_prev_uses_empty_string(self):
        """None prev_hash treated as empty string — chain starts clean."""
        h = compute_audit_hash("data", None)
        expected = hashlib.sha256("data".encode()).hexdigest()
        assert h == expected

    def test_hash_output_is_hex_64_chars(self):
        h = compute_audit_hash("anything", "prev")
        assert len(h) == 64
        int(h, 16)  # raises if not valid hex

    def test_chain_integrity_sequential(self):
        """Simulate a 3-entry chain — each hash depends on prior."""
        h1 = compute_audit_hash("event1", None)
        h2 = compute_audit_hash("event2", h1)
        h3 = compute_audit_hash("event3", h2)
        # Tamper event2 → h2 and h3 must change
        h2_tampered = compute_audit_hash("event2-TAMPERED", h1)
        h3_tampered = compute_audit_hash("event3", h2_tampered)
        assert h3 != h3_tampered


# ─── WB-09: Audit log API access control ─────────────────────────────────────

class TestAuditLogAPI:
    def test_get_audit_logs_requires_admin(self, client):
        resp = client.get("/api/audit/logs")
        assert resp.status_code in (401, 403)

    def test_get_audit_logs_viewer_forbidden(self, client):
        resp = client.get("/api/audit/logs", headers=viewer_headers())
        assert resp.status_code == 403

    def test_get_audit_logs_admin_returns_200(self, client):
        resp = client.get("/api/audit/logs", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert "total" in data

    def test_get_audit_logs_pagination(self, client):
        resp = client.get("/api/audit/logs?skip=0&limit=5", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["logs"]) <= 5

    def test_get_audit_logs_limit_max_100(self, client):
        """limit > 100 should be rejected (ge/le constraint)."""
        resp = client.get("/api/audit/logs?limit=200", headers=admin_headers())
        assert resp.status_code == 422

    def test_get_audit_logs_skip_negative_rejected(self, client):
        resp = client.get("/api/audit/logs?skip=-1", headers=admin_headers())
        assert resp.status_code == 422

    def test_get_audit_logs_filter_by_action(self, client):
        resp = client.get("/api/audit/logs?action=login", headers=admin_headers())
        assert resp.status_code == 200

    def test_get_audit_logs_filter_by_days(self, client):
        resp = client.get("/api/audit/logs?days=1", headers=admin_headers())
        assert resp.status_code == 200
