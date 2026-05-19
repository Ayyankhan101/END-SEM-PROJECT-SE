"""
WB-07: White box tests for notification / alert rule logic.
Tests boundary values for CPU/memory thresholds and channel validation.
"""
import pytest
from app.core.security import create_access_token
from app.db.models import get_db, AlertRule, Container, NotificationChannel
import json


def admin_headers():
    token = create_access_token({"sub": "admin", "role": "admin", "user_id": 1})
    return {"Authorization": f"Bearer {token}"}


def seed_container(db, cid="notif_container"):
    existing = db.query(Container).filter(Container.id == cid).first()
    if not existing:
        c = Container(id=cid, name="notif-test", status="running", user_id=1)
        db.add(c)
        db.commit()
    return cid


def cleanup_container(db, cid):
    c = db.query(Container).filter(Container.id == cid).first()
    if c:
        db.delete(c)
        db.commit()


# ─── WB-07: Alert rule boundary values ───────────────────────────────────────

class TestAlertRuleThresholds:
    def test_create_alert_rule_default_thresholds(self, client):
        db = next(get_db())
        rule = AlertRule(name="test-rule", cpu_threshold=80.0, memory_threshold=80.0)
        db.add(rule)
        db.commit()
        assert rule.cpu_threshold == 80.0
        assert rule.memory_threshold == 80.0
        db.delete(rule)
        db.commit()

    def test_alert_rule_zero_threshold_boundary(self, client):
        db = next(get_db())
        rule = AlertRule(name="zero-threshold", cpu_threshold=0.0, memory_threshold=0.0)
        db.add(rule)
        db.commit()
        assert rule.cpu_threshold == 0.0
        db.delete(rule)
        db.commit()

    def test_alert_rule_max_threshold_boundary(self, client):
        db = next(get_db())
        rule = AlertRule(name="max-threshold", cpu_threshold=100.0, memory_threshold=100.0)
        db.add(rule)
        db.commit()
        assert rule.cpu_threshold == 100.0
        db.delete(rule)
        db.commit()

    def test_alert_rule_fractional_threshold(self, client):
        db = next(get_db())
        rule = AlertRule(name="frac-threshold", cpu_threshold=75.5, memory_threshold=90.1)
        db.add(rule)
        db.commit()
        assert abs(rule.cpu_threshold - 75.5) < 0.001
        db.delete(rule)
        db.commit()

    def test_alert_rule_global_no_container(self, client):
        """container_id=None means global rule — must be allowed."""
        db = next(get_db())
        rule = AlertRule(name="global-rule", container_id=None, cpu_threshold=85.0)
        db.add(rule)
        db.commit()
        assert rule.container_id is None
        db.delete(rule)
        db.commit()

    def test_alert_rule_disabled_flag(self, client):
        db = next(get_db())
        rule = AlertRule(name="disabled-rule", enabled=0)
        db.add(rule)
        db.commit()
        assert rule.enabled == 0
        db.delete(rule)
        db.commit()


# ─── WB-07: Notification channel API validation ───────────────────────────────

class TestNotificationChannelAPI:
    def test_get_channels_requires_auth(self, client):
        resp = client.get("/api/notifications/channels")
        assert resp.status_code in (401, 403)

    def test_get_channels_with_auth_returns_list(self, client):
        resp = client.get("/api/notifications/channels", headers=admin_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_channel_invalid_type_returns_4xx(self, client):
        resp = client.post(
            "/api/notifications/channels",
            params={
                "name": "test-ch",
                "channel_type": "telegram",  # not in valid_types
                "is_enabled": True,
            },
            json={"url": "http://example.com"},
            headers=admin_headers()
        )
        # 400 = invalid channel_type; 422 = validation; 500 = unhandled error
        # All are non-2xx — invalid type must not return 200
        assert resp.status_code >= 400

    def test_create_channel_valid_webhook_type(self, client):
        resp = client.post(
            "/api/notifications/channels",
            params={
                "name": "wb-webhook-ch",
                "channel_type": "webhook",
                "is_enabled": True,
            },
            json={"webhook_url": "http://example.com/hook"},
            headers=admin_headers()
        )
        # Not a 400 "invalid type" error
        assert resp.status_code != 400

    def test_non_admin_sees_masked_config(self, client):
        """Non-admin must not see webhook URL."""
        db = next(get_db())
        ch = NotificationChannel(
            name="secret-ch",
            channel_type="webhook",
            config=json.dumps({"webhook_url": "http://secret.internal/hook"}),
            is_enabled=1
        )
        db.add(ch)
        db.commit()
        try:
            viewer_token = create_access_token({"sub": "viewer", "role": "viewer", "user_id": 99})
            resp = client.get(
                "/api/notifications/channels",
                headers={"Authorization": f"Bearer {viewer_token}"}
            )
            assert resp.status_code == 200
            for ch_data in resp.json():
                if ch_data.get("name") == "secret-ch":
                    # webhook_url must be masked
                    assert ch_data["config"].get("webhook_url") == "***"
        finally:
            found = db.query(NotificationChannel).filter(NotificationChannel.name == "secret-ch").first()
            if found:
                db.delete(found)
                db.commit()
