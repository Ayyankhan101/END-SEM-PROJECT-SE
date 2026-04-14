from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime as dt


class ContainerBase(BaseModel):
    id: str
    name: str
    image: Optional[str] = None
    status: Optional[str] = None


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


ContainerDetail.model_rebuild()