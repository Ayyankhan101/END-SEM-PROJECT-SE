from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import Container, Metric, Alert, RecoveryAction, Stack, Host
from app.models.schemas import (
    ContainerResponse,
    ContainerDetail,
    MetricResponse,
    AlertResponse,
    RecoveryActionResponse,
    LoginRequest,
    TokenResponse,
    ContainerConfig,
    StackCreate,
    StackResponse,
    HostCreate,
    HostResponse,
    SettingsUpdate,
    SettingsResponse,
)
from app.core.security import create_access_token, verify_password, get_current_user
from app.core.config import get_config
from app.core.rate_limiter import limiter
from app.core.validation import (
    validate_container_id,
    validate_container_name,
    validate_image_name,
    validate_positive_int,
)


router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.post("/auth/token")
@limiter.limit("10/minute")
async def login(
    request: Request, request_data: LoginRequest, db: Session = Depends(get_db)
):
    from app.db.models import User

    user = db.query(User).filter(User.username == request_data.username).first()
    if not user or not verify_password(
        request_data.password, str(user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token)


@router.get("/containers", response_model=List[ContainerResponse])
@limiter.limit("60/minute")
async def list_containers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    containers = db.query(Container).all()
    return containers


@router.get("/containers/{container_id}", response_model=ContainerDetail)
@limiter.limit("60/minute")
async def get_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    container = db.query(Container).filter(Container.id == validated_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container


@router.get("/containers/{container_id}/metrics")
async def get_container_metrics(
    container_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    metrics = (
        db.query(Metric)
        .filter(Metric.container_id == container_id)
        .order_by(Metric.timestamp.desc())
        .limit(limit)
        .all()
    )

    return {
        "container_id": container_id,
        "metrics": [
            {
                "id": m.id,
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "memory_usage": m.memory_usage,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in metrics
        ],
    }


@router.get("/metrics/history")
async def get_metrics_history(
    container_id: str = None,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in metrics
        ]
    }


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = 50,
    container_id: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Alert).order_by(Alert.timestamp.desc())

    if container_id:
        query = query.filter(Alert.container_id == container_id)

    alerts = query.limit(limit).all()
    return alerts


@router.post("/containers/{container_id}/restart")
@limiter.limit("30/minute")
async def restart_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    monitor = get_docker_monitor()
    success = monitor.restart_container(container_id)

    if success:
        action = RecoveryAction(
            container_id=container_id, action_type="restart", status="success"
        )
        db.add(action)
        db.commit()
        return {"status": "success", "message": f"Container {container_id} restarted"}
    else:
        action = RecoveryAction(
            container_id=container_id, action_type="restart", status="failed"
        )
        db.add(action)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to restart container")


@router.post("/containers/{container_id}/pause")
@limiter.limit("30/minute")
async def pause_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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
@limiter.limit("30/minute")
async def unpause_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    validated_id = validate_container_id(container_id)
    container = db.query(Container).filter(Container.id == validated_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    monitor = get_docker_monitor()
    success = monitor.unpause_container(container_id)

    if success:
        return {"status": "success", "message": f"Container {container_id} unpaused"}
    else:
        raise HTTPException(status_code=500, detail="Failed to unpause container")


@router.get("/containers/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    lines: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    monitor = get_docker_monitor()
    logs = monitor.get_container_logs(container_id, lines=lines)

    if logs is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")

    return {"container_id": container_id, "logs": logs}


@router.post("/containers")
@limiter.limit("20/minute")
async def create_container(
    request: Request,
    config: ContainerConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    result = monitor.create_container(config.model_dump())

    if not result:
        raise HTTPException(status_code=500, detail="Failed to create container")

    container = Container(
        id=result["id"],
        name=result["name"],
        image=result["image"],
        status=result["status"],
    )
    db.add(container)
    db.commit()

    return {"status": "success", "container": result}


@router.get("/stacks", response_model=List[StackResponse])
async def list_stacks(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    stacks = db.query(Stack).order_by(Stack.created_at.desc()).all()
    return stacks


@router.post("/stacks", response_model=StackResponse)
@limiter.limit("10/minute")
async def create_stack(
    request: Request,
    stack: StackCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    success = monitor.deploy_stack(stack.name, stack.compose_file)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to deploy stack")

    db_stack = Stack(name=stack.name, compose_file=stack.compose_file, status="running")
    db.add(db_stack)
    db.commit()
    db.refresh(db_stack)

    return db_stack


@router.delete("/stacks/{stack_id}")
async def delete_stack(
    stack_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    stack = db.query(Stack).filter(Stack.id == stack_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")

    monitor = get_docker_monitor()
    monitor.stop_stack(stack.name)

    db.delete(stack)
    db.commit()

    return {"status": "success", "message": f"Stack {stack.name} removed"}


@router.post("/stacks/{stack_id}/start")
@limiter.limit("20/minute")
async def start_stack(
    request: Request,
    stack_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    stack = db.query(Stack).filter(Stack.id == stack_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")

    monitor = get_docker_monitor()
    success = monitor.start_stack(stack.name, stack.compose_file)

    if success:
        stack.status = "running"
        db.commit()
        return {"status": "success", "message": f"Stack {stack.name} started"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start stack")


@router.post("/stacks/{stack_id}/stop")
@limiter.limit("20/minute")
async def stop_stack(
    request: Request,
    stack_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    stack = db.query(Stack).filter(Stack.id == stack_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Stack not found")

    monitor = get_docker_monitor()
    success = monitor.stop_stack(stack.name)

    if success:
        stack.status = "stopped"
        db.commit()
        return {"status": "success", "message": f"Stack {stack.name} stopped"}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop stack")


@router.get("/hosts", response_model=List[HostResponse])
async def list_hosts(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    hosts = db.query(Host).order_by(Host.last_seen.desc()).all()
    return hosts


@router.post("/hosts", response_model=HostResponse)
@limiter.limit("10/minute")
async def create_host(
    request: Request,
    host: HostCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    connected = monitor.test_host_connection(host.socket_path, host.api_version)

    db_host = Host(
        name=host.name,
        socket_path=host.socket_path,
        api_version=host.api_version,
        status="connected" if connected else "disconnected",
    )
    db.add(db_host)
    db.commit()
    db.refresh(db_host)

    return db_host


@router.delete("/hosts/{host_id}")
async def delete_host(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    db.delete(host)
    db.commit()

    return {"status": "success", "message": f"Host {host.name} removed"}


@router.post("/hosts/{host_id}/test")
@limiter.limit("20/minute")
async def test_host(
    request: Request,
    host_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    monitor = get_docker_monitor()
    connected = monitor.test_host_connection(host.socket_path, host.api_version)

    host.status = "connected" if connected else "disconnected"
    host.last_seen = datetime.utcnow()
    db.commit()

    return {"status": "success", "connected": connected}


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    config = get_config()
    return SettingsResponse(
        poll_interval=config.docker.poll_interval,
        cpu_threshold=config.monitoring.cpu_threshold,
        memory_threshold=config.monitoring.memory_threshold,
        metrics_ttl_days=config.database.metrics_ttl_days,
        recovery_enabled=config.recovery.enabled,
        jwt_expiration_hours=config.security.jwt_expiration_hours,
    )


@router.put("/settings", response_model=SettingsResponse)
@limiter.limit("10/minute")
async def update_settings(
    request: Request,
    settings: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    config = get_config()

    if settings.poll_interval is not None:
        config.docker.poll_interval = settings.poll_interval
    if settings.cpu_threshold is not None:
        config.monitoring.cpu_threshold = settings.cpu_threshold
    if settings.memory_threshold is not None:
        config.monitoring.memory_threshold = settings.memory_threshold
    if settings.metrics_ttl_days is not None:
        config.database.metrics_ttl_days = settings.metrics_ttl_days
    if settings.recovery_enabled is not None:
        config.recovery.enabled = settings.recovery_enabled

    return SettingsResponse(
        poll_interval=config.docker.poll_interval,
        cpu_threshold=config.monitoring.cpu_threshold,
        memory_threshold=config.monitoring.memory_threshold,
        metrics_ttl_days=config.database.metrics_ttl_days,
        recovery_enabled=config.recovery.enabled,
        jwt_expiration_hours=config.security.jwt_expiration_hours,
    )
enabled,
        jwt_expiration_hours=config.security.jwt_expiration_hours,
    )
