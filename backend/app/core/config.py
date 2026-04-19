import os
import warnings
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel

REQUIRED_ENV_VARS = ["DOCKWATCH_JWT_SECRET"]
MIN_JWT_SECRET_LENGTH = 32


def get_default_jwt_secret():
    """Generate a default JWT secret for development."""
    return "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"


def validate_environment() -> None:
    # Skip strict validation in development - use default secret if not set
    if os.environ.get("DOCKWATCH_JWT_SECRET"):
        jwt_secret = os.environ.get("DOCKWATCH_JWT_SECRET", "")
        if len(jwt_secret) < MIN_JWT_SECRET_LENGTH:
            raise EnvironmentError(
                f"DOCKWATCH_JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters long. "
            )


class DockerConfig(BaseModel):
    socket_path: str = "/var/run/docker.sock"
    api_version: str = "1.41"
    poll_interval: int = 5
    max_containers: int = 50


class MonitoringConfig(BaseModel):
    failure_detection_timeout: int = 30
    cpu_threshold: float = 90
    memory_threshold: float = 90
    pid_threshold: int = 1000


class RecoveryActionConfig(BaseModel):
    type: str
    max_attempts: int = 3
    delay: int = 5


class RecoveryConfig(BaseModel):
    enabled: bool = True
    actions: list[RecoveryActionConfig] = []


class DatabaseConfig(BaseModel):
    type: str = "sqlite"  # "sqlite" or "postgresql"
    path: str = "dockwatch.db"
    url: str = ""  # For PostgreSQL: postgresql://user:pass@host:5432/dbname
    metrics_ttl_days: int = 7


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class SecurityConfig(BaseModel):
    jwt_secret: str = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class CORSConfig(BaseModel):
    allowed_origins: list[str] = []
    allow_credentials: bool = True


class Config(BaseModel):
    docker: DockerConfig = DockerConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    recovery: RecoveryConfig = RecoveryConfig()
    database: DatabaseConfig = DatabaseConfig()
    server: ServerConfig = ServerConfig()
    security: SecurityConfig = SecurityConfig()
    logging: LoggingConfig = LoggingConfig()
    cors: Optional[CORSConfig] = None


_config: Optional[Config] = None


def load_config(config_path: Optional[str] = None) -> Config:
    global _config
    if _config is not None:
        return _config

    if config_path is None:
        config_path = os.environ.get("DOCKWATCH_CONFIG", "config/config.yaml")

    path = Path(config_path)
    if not path.exists():
        config = Config()
        _config = config
        return config

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    validate_environment()

    jwt_secret = os.environ.get("DOCKWATCH_JWT_SECRET")
    if jwt_secret:
        if "security" not in data:
            data["security"] = {}
        data["security"]["jwt_secret"] = jwt_secret

    _config = Config(**data)
    return _config


def get_config() -> Config:
    if _config is None:
        return load_config()
    return _config
