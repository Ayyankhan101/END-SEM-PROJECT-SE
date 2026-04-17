from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from pathlib import Path
import os


Base = declarative_base()


class Container(Base):
    __tablename__ = "containers"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    image = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    metrics = relationship("Metric", back_populates="container")
    alerts = relationship("Alert", back_populates="container")
    recovery_actions = relationship("RecoveryAction", back_populates="container")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"))
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    memory_usage = Column(Integer)
    timestamp = Column(DateTime, default=func.now())

    container = relationship("Container", back_populates="metrics")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"))
    alert_type = Column(String)
    message = Column(Text)
    severity = Column(String)
    timestamp = Column(DateTime, default=func.now())

    container = relationship("Container", back_populates="alerts")


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"))
    action_type = Column(String)
    status = Column(String)
    timestamp = Column(DateTime, default=func.now())

    container = relationship("Container", back_populates="recovery_actions")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    must_change_password = Column(Integer, default=0)  # 0 = false, 1 = true
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Stack(Base):
    __tablename__ = "stacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    compose_file = Column(Text, nullable=False)
    status = Column(String, default="stopped")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    socket_path = Column(String, default="unix:///var/run/docker.sock")
    api_version = Column(String, default="1.41")
    status = Column(String, default="disconnected")
    last_seen = Column(DateTime, default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    resource_type = Column(String, nullable=False)  # container, stack, host, settings, etc.
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    user = relationship("User")


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    channel_type = Column(String, nullable=False)  # email, webhook, slack, discord
    config = Column(Text, nullable=False)  # JSON string with channel-specific config
    is_enabled = Column(Integer, default=1)  # 0 = false, 1 = true
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"))
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    status = Column(String, nullable=False)  # sent, failed, pending
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    channel = relationship("NotificationChannel")
    alert = relationship("Alert")


_engine = None
_SessionLocal = None


def init_db(db_path: str = "dockwatch.db"):
    global _engine, _SessionLocal

    db_file = Path(db_path)
    if not db_file.is_absolute():
        db_file = Path(__file__).parent.parent.parent.parent / db_file

    _engine = create_engine(f"sqlite:///{db_file}", echo=False)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)


def get_db():
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()
