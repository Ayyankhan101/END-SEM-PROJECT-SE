from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey
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
    created_at = Column(DateTime, default=func.now())


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