"""
WB-08: White box tests for backup API.
Tests list, create (background task), and access control.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.security import create_access_token


def admin_headers():
    token = create_access_token({"sub": "admin", "role": "admin", "user_id": 1})
    return {"Authorization": f"Bearer {token}"}


def viewer_headers():
    token = create_access_token({"sub": "viewer", "role": "viewer", "user_id": 99})
    return {"Authorization": f"Bearer {token}"}


class TestBackupList:
    def test_list_backups_requires_auth(self, client):
        resp = client.get("/api/backup/list")
        assert resp.status_code in (401, 403)

    def test_list_backups_admin_returns_200(self, client):
        resp = client.get("/api/backup/list", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "backups" in data
        assert isinstance(data["backups"], list)

    def test_list_backups_viewer_allowed(self, client):
        """List is read-only — viewers can access."""
        resp = client.get("/api/backup/list", headers=viewer_headers())
        assert resp.status_code == 200


class TestBackupCreate:
    def test_create_backup_requires_auth(self, client):
        resp = client.post("/api/backup/create")
        assert resp.status_code in (401, 403)

    def test_create_backup_viewer_forbidden(self, client):
        """require_admin dependency must block non-admins."""
        resp = client.post("/api/backup/create", headers=viewer_headers())
        assert resp.status_code == 403

    def test_create_backup_admin_queues_task(self, client):
        """Background task should be added — response 200 with filename."""
        with patch("app.api.backup.create_backup_archive") as mock_archive:
            mock_archive.return_value = None
            resp = client.post("/api/backup/create", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "filename" in data
        assert data["filename"].startswith("dockwatch_backup_")

    def test_create_backup_no_metrics_flag(self, client):
        """include_metrics=false should still succeed."""
        with patch("app.api.backup.create_backup_archive") as mock_archive:
            mock_archive.return_value = None
            resp = client.post(
                "/api/backup/create?include_metrics=false",
                headers=admin_headers()
            )
        assert resp.status_code == 200
