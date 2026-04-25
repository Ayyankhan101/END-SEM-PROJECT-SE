from datetime import datetime
from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime as dt


class ContainerBase(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    status: Optional[str] = None
    group: Optional[str] = "default"


class ContainerCreate(ContainerBase):
    pass


class ContainerResponse(ContainerBase):
    created_at: Optional[dt] = None
    last_updated: Optional[dt] = None

    class Config:
        from_attributes = True


class ContainerDetail(ContainerResponse):
    metrics: List["MetricResponse"] = []
    alerts: List["AlertResponse"] = []
    config: Optional[dict] = None
    network_settings: Optional[dict] = None


class MetricBase(BaseModel):
    container_id: str
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_usage: Optional[int] = None


class MetricCreate(MetricBase):
    pass


class MetricResponse(MetricBase):
    id: int
    timestamp: Optional[dt] = None

    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    container_id: str
    alert_type: str
    message: str
    severity: str


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    id: int
    timestamp: Optional[dt] = None

    class Config:
        from_attributes = True


class RecoveryActionBase(BaseModel):
    container_id: str
    action_type: str
    status: str


class RecoveryActionCreate(RecoveryActionBase):
    pass


class RecoveryActionResponse(RecoveryActionBase):
    id: int
    timestamp: Optional[dt] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: Optional[bool] = False
    user_id: Optional[int] = None


class ContainerConfig(BaseModel):
    image: str
    name: str
    ports: Optional[dict] = None
    volumes: Optional[List[dict]] = None
    environment: Optional[dict] = None
    command: Optional[str] = None
    memory_limit: Optional[int] = None
    cpu_limit: Optional[float] = None


class ContainerCreateResponse(BaseModel):
    id: str
    name: str
    image: str
    status: str
    message: str


class StackBase(BaseModel):
    name: str
    compose_file: str


class StackCreate(StackBase):
    pass


class StackResponse(StackBase):
    id: int
    status: str
    created_at: Optional[dt] = None
    updated_at: Optional[dt] = None

    class Config:
        from_attributes = True


class HostBase(BaseModel):
    name: str
    socket_path: Optional[str] = "unix:///var/run/docker.sock"
    api_version: Optional[str] = "1.41"


class HostCreate(HostBase):
    pass


class HostResponse(HostBase):
    id: int
    status: str
    last_seen: Optional[dt] = None

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    poll_interval: Optional[int] = None
    cpu_threshold: Optional[float] = None
    memory_threshold: Optional[float] = None
    metrics_ttl_days: Optional[int] = None
    recovery_enabled: Optional[bool] = None


class SettingsResponse(BaseModel):
    poll_interval: int
    cpu_threshold: float
    memory_threshold: float
    metrics_ttl_days: int
    recovery_enabled: bool
    jwt_expiration_hours: int


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    must_change_password: Optional[bool] = None
    force_password_change: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: Optional[datetime] = None
    must_change_password: bool = False


class ContainerUpdate(BaseModel):
    group: Optional[str] = None
    is_favorite: Optional[bool] = None


class AlertRuleCreate(BaseModel):
    container_id: Optional[str] = None
    name: str
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    cpu_threshold: Optional[float] = None
    memory_threshold: Optional[float] = None
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: int
    container_id: Optional[str]
    name: str
    cpu_threshold: float
    memory_threshold: float
    enabled: bool
    created_at: Optional[datetime] = None


class ScheduleCreate(BaseModel):
    container_id: str
    action: str
    time: str

    @validator('time')
    def validate_time_format(cls, v):
        import re
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Time must be in HH:MM format (00:00-23:59)')
        return v

    @validator('action')
    def validate_action(cls, v):
        if v not in ['start', 'stop', 'restart']:
            raise ValueError('Action must be start, stop, or restart')
        return v


class ScheduleUpdate(BaseModel):
    action: Optional[str] = None
    time: Optional[str] = None
    enabled: Optional[bool] = None

    @validator('time')
    def validate_time_format(cls, v):
        if v is None:
            return v
        import re
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Time must be in HH:MM format (00:00-23:59)')
        return v

    @validator('action')
    def validate_action(cls, v):
        if v is None:
            return v
        if v not in ['start', 'stop', 'restart']:
            raise ValueError('Action must be start, stop, or restart')
        return v


class ScheduleResponse(BaseModel):
    id: int
    container_id: str
    container_name: Optional[str] = None
    action: str
    time: str
    enabled: bool
    created_at: Optional[datetime] = None


class ExecCreate(BaseModel):
    cmd: List[str]
    tty: bool = True
    stdin: bool = False


ContainerDetail.model_rebuild()
