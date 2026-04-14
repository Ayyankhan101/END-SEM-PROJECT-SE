from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import Container, Metric, Alert, RecoveryAction
from app.models.schemas import (
    ContainerResponse, ContainerDetail,
    MetricResponse, AlertResponse, RecoveryActionResponse,
    LoginRequest, TokenResponse
)
from app.core.security import create_access_token, verify_password, get_current_user


router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.post("/auth/token", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    from app.db.models import User
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, str(user.hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token)


@router.get("/containers", response_model=List[ContainerResponse])
async def list_containers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    containers = db.query(Container).all()
    return containers


@router.get("/containers/{container_id}", response_model=ContainerDetail)
async def get_container(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container


@router.get("/containers/{container_id}/metrics")
async def get_container_metrics(
    container_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    metrics = db.query(Metric).filter(
        Metric.container_id == container_id
    ).order_by(Metric.timestamp.desc()).limit(limit).all()
    
    return {
        "container_id": container_id,
        "metrics": [
            {
                "id": m.id,
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "memory_usage": m.memory_usage,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in metrics
        ]
    }


@router.get("/metrics/history")
async def get_metrics_history(
    container_id: str = None,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(Metric).filter(Metric.timestamp >= cutoff)
    
    if container_id:
        query = query.filter(Metric.container_id == container_id)
    
    metrics = query.order_by(Metric.timestamp.desc()).all()
    
    return {
        "metrics": [
            {
                "container_id": m.container_id,
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "memory_usage": m.memory_usage,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in metrics
        ]
    }


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = 50,
    container_id: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Alert).order_by(Alert.timestamp.desc())
    
    if container_id:
        query = query.filter(Alert.container_id == container_id)
    
    alerts = query.limit(limit).all()
    return alerts


@router.post("/containers/{container_id}/restart")
async def restart_container(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.docker_monitor import get_docker_monitor
    
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    monitor = get_docker_monitor()
    success = monitor.restart_container(container_id)
    
    if success:
        action = RecoveryAction(
            container_id=container_id,
            action_type="restart",
            status="success"
        )
        db.add(action)
        db.commit()
        return {"status": "success", "message": f"Container {container_id} restarted"}
    else:
        action = RecoveryAction(
            container_id=container_id,
            action_type="restart",
            status="failed"
        )
        db.add(action)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to restart container")


@router.post("/containers/{container_id}/pause")
async def pause_container(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.docker_monitor import get_docker_monitor
    
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    monitor = get_docker_monitor()
    success = monitor.pause_container(container_id)
    
    if success:
        return {"status": "success", "message": f"Container {container_id} paused"}
    else:
        raise HTTPException(status_code=500, detail="Failed to pause container")


@router.post("/containers/{container_id}/unpause")
async def unpause_container(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from app.services.docker_monitor import get_docker_monitor
    
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    monitor = get_docker_monitor()
    success = monitor.unpause_container(container_id)
    
    if success:
        return {"status": "success", "message": f"Container {container_id} unpaused"}
    else:
        raise HTTPException(status_code=500, detail="Failed to unpause container")