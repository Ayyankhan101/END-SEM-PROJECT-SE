import os
import warnings
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))

logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ["DOCKWATCH_JWT_SECRET"]
MIN_JWT_SECRET_LENGTH = 32


def get_default_jwt_secret():
    """Generate JWT secret - dev fallback with production check."""
    secret = os.environ.get("DOCKWATCH_JWT_SECRET", "")
    env = os.environ.get("ENV", "development")
    
    if secret:
        if len(secret) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"DOCKWATCH_JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters long. "
            )
        return secret
    
    if env == "production":
        raise ValueError(
            "DOCKWATCH_JWT_SECRET environment variable must be set in production. "
            "Set ENV=development for development mode."
        )
    
    # No fallback - secret must be set
    raise ValueError(
        "DOCKWATCH_JWT_SECRET must be set. Set it in .env or environment variables."
    )


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

    def __init__(self, **data):
        super().__init__(**data)
        # Override socket_path from environment variable
        env_socket = os.environ.get("DOCKWATCH_DOCKER_SOCKET")
        if env_socket:
            self.socket_path = env_socket


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
    jwt_secret: str = ""  # Must be set via get_default_jwt_secret()
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    def __init__(self, **data):
        if not data.get("jwt_secret"):
            data["jwt_secret"] = get_default_jwt_secret()
        super().__init__(**data)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class CORSConfig(BaseModel):
    allowed_origins: list[str] = []
    allow_credentials: bool = True


class AIConfig(BaseModel):
    provider: str = "ollama"  # "ollama", "openai", "anthropic", "together"
    api_key: str = ""
    endpoint: str = "http://localhost:11434"
    model: str = "llama3"


class Config(BaseModel):
    docker: DockerConfig = DockerConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    recovery: RecoveryConfig = RecoveryConfig()
    database: DatabaseConfig = DatabaseConfig()
    server: ServerConfig = ServerConfig()
    security: SecurityConfig = SecurityConfig()
    logging: LoggingConfig = LoggingConfig()
    cors: Optional[CORSConfig] = None
    ai: Optional[AIConfig] = None


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
