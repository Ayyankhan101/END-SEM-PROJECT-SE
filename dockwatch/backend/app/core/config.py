import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel


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
    path: str = "dockwatch.db"
    metrics_ttl_days: int = 7


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class SecurityConfig(BaseModel):
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Config(BaseModel):
    docker: DockerConfig = DockerConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    recovery: RecoveryConfig = RecoveryConfig()
    database: DatabaseConfig = DatabaseConfig()
    server: ServerConfig = ServerConfig()
    security: SecurityConfig = SecurityConfig()
    logging: LoggingConfig = LoggingConfig()


_config: Optional[Config] = None


def load_config(config_path: Optional[str] = None) -> Config:
    global _config
    if _config is not None:
        return _config
    
    if config_path is None:
        config_path = os.environ.get("DOCKWATCH_CONFIG", "config/config.yaml")
    
    path = Path(config_path)
    if not path.exists():
        return Config()
    
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    
    _config = Config(**data)
    return _config


def get_config() -> Config:
    if _config is None:
        return load_config()
    return _config