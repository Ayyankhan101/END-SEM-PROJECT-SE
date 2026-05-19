"""
WB-03, WB-04, WB-10: White box tests for container endpoints.
Mocks Docker monitor — tests auth, ownership, success/failure paths.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.core.security import create_access_token
from app.db.models import Container, get_db


def make_admin_token():
    return create_access_token({"sub": "admin", "role": "admin", "user_id": 1})


def make_viewer_token(user_id=99):
    return create_access_token({"sub": "viewer", "role": "viewer", "user_id": user_id})


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ─── Helpers: seed / clean a container row ────────────────────────────────────

def seed_container(db, cid="abc123", user_id=None):
    existing = db.query(Container).filter(Container.id == cid).first()
    if existing:
        return existing
    c = Container(id=cid, name="test-container", status="running", user_id=user_id)
    db.add(c)
    db.commit()
    return c


def remove_container(db, cid="abc123"):
    c = db.query(Container).filter(Container.id == cid).first()
    if c:
        db.delete(c)
        db.commit()


# ─── WB-03: Container start ───────────────────────────────────────────────────

class TestContainerStart:
    def test_start_success(self, client):
        db = next(get_db())
        seed_container(db, "start_ok")
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.start_container.return_value = True
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/start_ok/start",
                    headers=auth_headers(make_admin_token())
                )
            assert resp.status_code == 200
            assert resp.json()["status"] == "success"
        finally:
            remove_container(db, "start_ok")

    def test_start_docker_failure_returns_500(self, client):
        db = next(get_db())
        seed_container(db, "start_fail")
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.start_container.return_value = False
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/start_fail/start",
                    headers=auth_headers(make_admin_token())
                )
            assert resp.status_code == 500
        finally:
            remove_container(db, "start_fail")

    def test_start_unauthenticated_returns_401(self, client):
        resp = client.post("/api/containers/any_id/start")
        assert resp.status_code in (401, 403)


# ─── WB-03: Container stop ────────────────────────────────────────────────────

class TestContainerStop:
    def test_stop_success(self, client):
        db = next(get_db())
        seed_container(db, "stop_ok")
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.stop_container.return_value = True
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/stop_ok/stop",
                    headers=auth_headers(make_admin_token())
                )
            assert resp.status_code == 200
            assert resp.json()["status"] == "success"
        finally:
            remove_container(db, "stop_ok")

    def test_stop_failure_returns_500(self, client):
        db = next(get_db())
        seed_container(db, "stop_fail")
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.stop_container.return_value = False
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/stop_fail/stop",
                    headers=auth_headers(make_admin_token())
                )
            assert resp.status_code == 500
        finally:
            remove_container(db, "stop_fail")


# ─── WB-03: Container restart ─────────────────────────────────────────────────

class TestContainerRestart:
    def test_restart_success(self, client):
        db = next(get_db())
        seed_container(db, "restart_ok")
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.restart_container.return_value = True
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/restart_ok/restart",
                    headers=auth_headers(make_admin_token())
                )
            assert resp.status_code == 200
        finally:
            remove_container(db, "restart_ok")

    def test_restart_failure_returns_500(self, client):
        db = next(get_db())
        seed_container(db, "restart_fail")
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.restart_container.return_value = False
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/restart_fail/restart",
                    headers=auth_headers(make_admin_token())
                )
            assert resp.status_code == 500
        finally:
            remove_container(db, "restart_fail")


# ─── WB-04: Container not found → 404 ────────────────────────────────────────

class TestContainerNotFound:
    def test_start_nonexistent_container_returns_404(self, client):
        resp = client.post(
            "/api/containers/does_not_exist_xyz/start",
            headers=auth_headers(make_admin_token())
        )
        assert resp.status_code == 404

    def test_stop_nonexistent_container_returns_404(self, client):
        resp = client.post(
            "/api/containers/does_not_exist_xyz/stop",
            headers=auth_headers(make_admin_token())
        )
        assert resp.status_code == 404

    def test_restart_nonexistent_container_returns_404(self, client):
        resp = client.post(
            "/api/containers/does_not_exist_xyz/restart",
            headers=auth_headers(make_admin_token())
        )
        assert resp.status_code == 404

    def test_get_nonexistent_container_returns_404_or_400(self, client):
        resp = client.get(
            "/api/containers/does_not_exist_xyz",
            headers=auth_headers(make_admin_token())
        )
        # 404 if container not found; 400 if ID fails validation
        assert resp.status_code in (404, 400)


# ─── Ownership: viewer cannot access another user's container ─────────────────

class TestContainerOwnership:
    def test_viewer_cannot_start_other_users_container(self, client):
        db = next(get_db())
        # Seed container with user_id=None; viewer token has user_id=99
        # check_container_ownership: None != 99 → 403
        seed_container(db, "owner_check", user_id=None)
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.start_container.return_value = True
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/owner_check/start",
                    headers=auth_headers(make_viewer_token(user_id=99))
                )
            assert resp.status_code == 403
        finally:
            remove_container(db, "owner_check")

    def test_admin_can_start_any_container(self, client):
        db = next(get_db())
        seed_container(db, "admin_any", user_id=None)
        try:
            with patch("app.services.docker_monitor.get_docker_monitor") as mock_gm:
                monitor = MagicMock()
                monitor._container_service = MagicMock()
                monitor.start_container.return_value = True
                mock_gm.return_value = monitor
                resp = client.post(
                    "/api/containers/admin_any/start",
                    headers=auth_headers(make_admin_token())
                )
            assert resp.status_code == 200
        finally:
            remove_container(db, "admin_any")
