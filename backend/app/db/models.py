from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    text,
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
    group = Column(String, default="default")
    is_favorite = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    metrics = relationship("Metric", back_populates="container", lazy="selectin")
    alerts = relationship("Alert", back_populates="container", lazy="selectin")
    recovery_actions = relationship("RecoveryAction", back_populates="container", lazy="selectin")
    alert_rules = relationship("AlertRule", back_populates="container", lazy="selectin")
    schedules = relationship("Schedule", back_populates="container", lazy="selectin")
    owner = relationship("User", back_populates="containers")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"), index=True)
    action = Column(String, nullable=False)  # start, stop, restart
    time = Column(String, nullable=False)  # HH:MM format
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    container = relationship("Container", back_populates="schedules")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"), nullable=True, index=True)  # null = global rule
    name = Column(String, nullable=False)
    cpu_threshold = Column(Float, default=80.0)
    memory_threshold = Column(Float, default=80.0)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    container = relationship("Container", back_populates="alert_rules")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"), index=True)
    cpu_percent = Column(Float)
    memory_percent = Column(Float)
    memory_usage = Column(Integer)
    timestamp = Column(DateTime, default=func.now())

    container = relationship("Container", back_populates="metrics")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"), index=True)
    alert_type = Column(String)
    message = Column(Text)
    severity = Column(String)
    timestamp = Column(DateTime, default=func.now())

    container = relationship("Container", back_populates="alerts")


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    container_id = Column(String, ForeignKey("containers.id"), index=True)
    action_type = Column(String)
    status = Column(String)
    timestamp = Column(DateTime, default=func.now())

    container = relationship("Container", back_populates="recovery_actions")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    totp_secret = Column(String, nullable=True)
    is_2fa_enabled = Column(Integer, default=0)
    backup_codes = Column(String, nullable=True)  # Encrypted JSON list of codes
    must_change_password = Column(Integer, default=0)
    force_password_change = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime, nullable=True)
    tokens_revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    containers = relationship("Container", back_populates="owner")


class Stack(Base):
    __tablename__ = "stacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    compose_file = Column(Text, nullable=False)
    status = Column(String, default="stopped")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    owner = relationship("User")


class DockerResource(Base):
    __tablename__ = "docker_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_type = Column(String, nullable=False)  # image, volume, network
    resource_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())

    owner = relationship("User")


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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())
    hash_chain = Column(String, nullable=True)

    user = relationship("User")


def get_last_audit_hash(session) -> str | None:
    """Get the last hash_chain value from audit logs."""
    result = session.query(AuditLog.hash_chain).order_by(AuditLog.id.desc()).first()
    return result[0] if result else None


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    channel_type = Column(String, nullable=False)
    config = Column(Text, nullable=False)
    is_enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)


class RegistryCredential(Base):
    __tablename__ = "registry_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_url = Column(String, nullable=False, index=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)  # Encrypted
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())

    owner = relationship("User")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("notification_channels.id"), index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True, index=True)
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    channel = relationship("NotificationChannel")
    alert = relationship("Alert")


_engine = None
_SessionLocal = None


def init_db(db_type: str = None, db_path: str = None, db_url: str = None):
    global _engine, _SessionLocal

    from app.core.config import get_config
    config = get_config()
    
    if db_type is None:
        db_type = config.database.type
    if db_path is None:
        db_path = config.database.path
    if db_url is None:
        db_url = config.database.url

    if db_type == "postgresql" and db_url:
        _engine = create_engine(db_url, echo=False, pool_pre_ping=True)
    else:
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "data" / "dockwatch.db"

        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not db_file.exists():
            db_file.touch()
            db_file.chmod(0o600)
            db_file.parent.chmod(0o700)
        
        _engine = create_engine(
            f"sqlite:///{db_file}", echo=False, connect_args={"check_same_thread": False}
        )
        
        with _engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.execute(text("PRAGMA busy_timeout=5000"))
            conn.commit()
    
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
