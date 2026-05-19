"""
WB-11: White box tests for Pydantic schema validation.
Tests required fields, type coercion, default values, and rejection of bad input.
"""
import pytest
from pydantic import ValidationError
from app.models.schemas import (
    LoginRequest,
    TokenResponse,
    ContainerConfig,
    UserCreate,
    UserUpdate,
    SettingsUpdate,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    ContainerBase,
    MetricBase,
)
from datetime import datetime


# ─── LoginRequest ─────────────────────────────────────────────────────────────

class TestLoginRequest:
    def test_valid_login_request(self):
        req = LoginRequest(username="admin", password="secret")
        assert req.username == "admin"

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="admin")

    def test_empty_fields_allowed_by_schema(self):
        """Schema doesn't enforce non-empty — that's the endpoint's job."""
        req = LoginRequest(username="", password="")
        assert req.username == ""


# ─── TokenResponse ────────────────────────────────────────────────────────────

class TestTokenResponse:
    def test_defaults(self):
        resp = TokenResponse(access_token="tok123", user_id=5)
        assert resp.token_type == "bearer"
        assert resp.requires_2fa is False
        assert resp.user_id == 5

    def test_requires_2fa_flag(self):
        resp = TokenResponse(access_token="tok", requires_2fa=True, user_id=1)
        assert resp.requires_2fa is True

    def test_missing_access_token_raises(self):
        with pytest.raises(ValidationError):
            TokenResponse(user_id=1)


# ─── ContainerConfig ──────────────────────────────────────────────────────────

class TestContainerConfig:
    def test_minimal_valid(self):
        cfg = ContainerConfig(image="nginx:latest", name="my-nginx")
        assert cfg.ports is None
        assert cfg.memory_limit is None

    def test_missing_image_raises(self):
        with pytest.raises(ValidationError):
            ContainerConfig(name="no-image")

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            ContainerConfig(image="nginx:latest")

    def test_full_config(self):
        cfg = ContainerConfig(
            image="redis:7",
            name="redis",
            ports={"6379/tcp": 6379},
            environment={"REDIS_PASSWORD": "secret"},
            memory_limit=512,
            cpu_limit=0.5
        )
        assert cfg.memory_limit == 512
        assert cfg.cpu_limit == 0.5


# ─── UserCreate ───────────────────────────────────────────────────────────────

class TestUserCreate:
    def test_default_role_is_user(self):
        u = UserCreate(username="bob", password="pass123")
        assert u.role == "user"

    def test_custom_role(self):
        u = UserCreate(username="bob", password="pass123", role="admin")
        assert u.role == "admin"

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(password="pass123")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(username="bob")


# ─── SettingsUpdate ───────────────────────────────────────────────────────────

class TestSettingsUpdate:
    def test_all_optional_none_by_default(self):
        s = SettingsUpdate()
        assert s.poll_interval is None
        assert s.cpu_threshold is None
        assert s.recovery_enabled is None

    def test_partial_update(self):
        s = SettingsUpdate(cpu_threshold=90.0)
        assert s.cpu_threshold == 90.0
        assert s.memory_threshold is None

    def test_wrong_type_raises(self):
        with pytest.raises(ValidationError):
            SettingsUpdate(poll_interval="not-a-number")


# ─── AlertRuleCreate ──────────────────────────────────────────────────────────

class TestAlertRuleCreate:
    def test_defaults(self):
        rule = AlertRuleCreate(name="my-rule")
        assert rule.cpu_threshold == 80.0
        assert rule.memory_threshold == 80.0
        assert rule.enabled is True
        assert rule.container_id is None

    def test_custom_thresholds(self):
        rule = AlertRuleCreate(name="custom", cpu_threshold=95.0, memory_threshold=70.0)
        assert rule.cpu_threshold == 95.0

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            AlertRuleCreate(cpu_threshold=80.0)

    def test_string_threshold_coerced_to_float(self):
        """Pydantic coerces compatible string → float."""
        rule = AlertRuleCreate(name="coerce", cpu_threshold="75.0")
        assert rule.cpu_threshold == 75.0


# ─── MetricBase ───────────────────────────────────────────────────────────────

class TestMetricBase:
    def test_all_metrics_optional_except_container_id(self):
        m = MetricBase(container_id="abc")
        assert m.cpu_percent is None
        assert m.memory_percent is None

    def test_full_metric(self):
        m = MetricBase(container_id="abc", cpu_percent=55.2, memory_percent=30.1, memory_usage=1024)
        assert m.cpu_percent == 55.2

    def test_missing_container_id_raises(self):
        with pytest.raises(ValidationError):
            MetricBase(cpu_percent=10.0)
