from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pydantic import validator
import logging

logger = logging.getLogger(__name__)

from app.db.models import get_db
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
from app.core.security import create_access_token, verify_password, get_current_user, get_password_hash, get_user_role
from app.core.config import get_config
from app.core.rate_limiter import limiter
from app.core.validation import (
    validate_container_id,
    validate_container_name,
    validate_image_name,
    validate_positive_int,
)
from pydantic import BaseModel


router = APIRouter()


@router.post("/auth/token")
@limiter.limit("10/minute")
async def login(
    request: Request, request_data: LoginRequest, db: Session = Depends(get_db)
):
    from app.db.models import User
    import pyotp

    user = db.query(User).filter(User.username == request_data.username).first()
    if not user or not verify_password(request_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    if user.is_2fa_enabled and user.totp_secret:
        return TokenResponse(access_token="", requires_2fa=True, user_id=user.id)
    
    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, user_id=user.id)


@router.post("/auth/2fa/verify")
@limiter.limit("10/minute")
async def verify_2fa(
    request: Request,
    user_id: int,
    code: str,
    db: Session = Depends(get_db)
):
    from app.db.models import User
    import pyotp

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not configured")
    
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, user_id=user.id)


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str


@router.post("/auth/2fa/setup", response_model=TOTPSetupResponse)
@limiter.limit("10/minute")
async def setup_2fa(
    request: Request,
    user_id: int,
    code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import User
    import pyotp
    import qrcode
    import io
    import base64

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If user already has TOTP secret and code provided, verify it
    if user.totp_secret and code:
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code):
            raise HTTPException(status_code=401, detail="Invalid verification code")
        
        user.is_2fa_enabled = 1
        db.commit()
        return {"secret": user.totp_secret, "qr_code": ""}
    
    # If no secret exists, generate new one for initial setup
    
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()
    
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(user.username, "DockWatch")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    
    return {"secret": secret, "qr_code": qr_code}


@router.post("/auth/2fa/disable")
@limiter.limit("10/minute")
async def disable_2fa(
    request: Request,
    user_id: int,
    code: str,
    password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import User
    import pyotp

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    
    if user.totp_secret:
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    user.totp_secret = None
    user.is_2fa_enabled = 0
    db.commit()
    
    return {"status": "success", "message": "2FA disabled"}


@router.post("/auth/logout-all")
@limiter.limit("5/minute")
async def logout_all_devices(
    request: Request,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import User
    
    username = current_user.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"status": "success", "message": "All sessions invalidated. Please login with new password."}


@router.get("/containers", response_model=List[ContainerResponse])
@limiter.limit("60/minute")
async def list_containers(
    request: Request,
    favorites: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Container)
    if favorites:
        query = query.filter(Container.is_favorite == 1)
    containers = query.all()
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
    
    from app.services.docker_monitor import get_docker_monitor
    monitor = get_docker_monitor()
    docker_info = monitor.get_container(container_id)
    
    if docker_info:
        container.config = docker_info.get("config", {})
        container.network_settings = docker_info.get("network_settings", {})
    
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
    request: Request,
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
    request: Request,
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


@router.post("/containers/{container_id}/stop")
@limiter.limit("30/minute")
async def stop_container(
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
    success = monitor.stop_container(container_id)

    if success:
        return {"status": "success", "message": f"Container {container_id} stopped"}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop container")


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


@router.post("/hosts/{host_id}/activate")
@limiter.limit("10/minute")
async def activate_host(
    request: Request,
    host_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Activate a Docker host (switch current connection)."""
    from app.services.docker_monitor import get_docker_monitor

    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    monitor = get_docker_monitor()
    connected = monitor.switch_host(host.socket_path, host.api_version)

    host.status = "connected" if connected else "disconnected"
    host.last_seen = datetime.utcnow()
    db.commit()

    return {"status": "success", "connected": connected, "host": host.name}


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


@router.post("/containers/bulk/start")
async def bulk_start_containers(
    request: Request,
    container_ids: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    results = []
    for container_id in container_ids:
        container = db.query(Container).filter(Container.id == container_id).first()
        if container:
            success = monitor.restart_container(container_id)
            results.append({"id": container_id, "success": success})
    
    return {"status": "success", "results": results}


@router.post("/containers/bulk/stop")
async def bulk_stop_containers(
    request: Request,
    container_ids: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    results = []
    for container_id in container_ids:
        container = db.query(Container).filter(Container.id == container_id).first()
        if container:
            success = monitor.stop_container(container_id)
            results.append({"id": container_id, "success": success})
    
    return {"status": "success", "results": results}


@router.post("/containers/bulk/restart")
async def bulk_restart_containers(
    request: Request,
    container_ids: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    results = []
    for container_id in container_ids:
        container = db.query(Container).filter(Container.id == container_id).first()
        if container:
            success = monitor.restart_container(container_id)
            results.append({"id": container_id, "success": success})
    
    return {"status": "success", "results": results}


@router.post("/containers/bulk/delete")
async def bulk_delete_containers(
    request: Request,
    container_ids: List[str],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for bulk delete"
        )

    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    results = []
    for container_id in container_ids:
        container = db.query(Container).filter(Container.id == container_id).first()
        if container:
            try:
                success = monitor.remove_container(container_id)
                if success:
                    db.delete(container)
                    db.commit()
                results.append({"id": container_id, "success": success})
            except Exception as e:
                logger.error(f"Failed to delete container {container_id}: {e}", exc_info=True)
                results.append({"id": container_id, "success": False, "error": str(e)})
    
    return {"status": "success", "results": results}


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


@router.put("/containers/{container_id}/env")
async def update_container_env(
    request: Request,
    container_id: str,
    env_vars: Dict[str, str],
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    success = monitor.update_container_env(validated_id, env_vars)
    
    if success:
        return {"status": "success", "message": "Environment updated"}
    raise HTTPException(status_code=500, detail="Failed to update environment")


@router.put("/containers/{container_id}/ports")
async def update_container_ports(
    request: Request,
    container_id: str,
    ports: Dict[str, int],
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    success = monitor.update_container_ports(validated_id, ports)
    
    if success:
        return {"status": "success", "message": "Ports updated"}
    raise HTTPException(status_code=500, detail="Failed to update ports")


@router.put("/containers/{container_id}", response_model=ContainerResponse)
async def update_container(
    container_id: str,
    container_data: ContainerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    container = db.query(Container).filter(Container.id == validated_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    if container_data.group is not None:
        container.group = container_data.group
    
    db.commit()
    db.refresh(container)
    return container


@router.get("/containers/group/{group}", response_model=List[ContainerResponse])
async def list_containers_by_group(
    group: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    containers = db.query(Container).filter(Container.group == group).all()
    return containers


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    from app.db.models import User
    users = db.query(User).all()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            role=u.role or "user",
            created_at=u.created_at,
            must_change_password=bool(u.must_change_password)
        )
        for u in users
    ]


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    from app.db.models import User
    
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        must_change_password=0
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role or "user",
        created_at=user.created_at,
        must_change_password=bool(user.must_change_password)
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    from app.db.models import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)
    if user_data.role:
        user.role = user_data.role
    if user_data.must_change_password is not None:
        user.must_change_password = 1 if user_data.must_change_password else 0
    if user_data.force_password_change is not None:
        user.must_change_password = 1 if user_data.force_password_change else 0
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role or "user",
        created_at=user.created_at,
        must_change_password=bool(user.must_change_password)
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    from app.db.models import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the primary admin user"
        )
    
    db.delete(user)
    db.commit()
    
    return {"status": "success", "message": f"User {user.username} deleted"}


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


@router.get("/alert-rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    container_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import AlertRule
    
    query = db.query(AlertRule)
    if container_id:
        query = query.filter(AlertRule.container_id == container_id)
    
    rules = query.all()
    return [
        AlertRuleResponse(
            id=r.id,
            container_id=r.container_id,
            name=r.name,
            cpu_threshold=r.cpu_threshold,
            memory_threshold=r.memory_threshold,
            enabled=bool(r.enabled),
            created_at=r.created_at
        )
        for r in rules
    ]


@router.post("/alert-rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or user role required"
        )
    
    from app.db.models import AlertRule
    
    rule = AlertRule(
        container_id=rule_data.container_id,
        name=rule_data.name,
        cpu_threshold=rule_data.cpu_threshold,
        memory_threshold=rule_data.memory_threshold,
        enabled=1 if rule_data.enabled else 0
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return AlertRuleResponse(
        id=rule.id,
        container_id=rule.container_id,
        name=rule.name,
        cpu_threshold=rule.cpu_threshold,
        memory_threshold=rule.memory_threshold,
        enabled=bool(rule.enabled),
        created_at=rule.created_at
    )


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or user role required"
        )
    
    from app.db.models import AlertRule
    
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.cpu_threshold is not None:
        rule.cpu_threshold = rule_data.cpu_threshold
    if rule_data.memory_threshold is not None:
        rule.memory_threshold = rule_data.memory_threshold
    if rule_data.enabled is not None:
        rule.enabled = 1 if rule_data.enabled else 0
    
    db.commit()
    db.refresh(rule)
    
    return AlertRuleResponse(
        id=rule.id,
        container_id=rule.container_id,
        name=rule.name,
        cpu_threshold=rule.cpu_threshold,
        memory_threshold=rule.memory_threshold,
        enabled=bool(rule.enabled),
        created_at=rule.created_at
    )


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or user role required"
        )
    
    from app.db.models import AlertRule
    
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )
    
    db.delete(rule)
    db.commit()
    
    return {"status": "success", "message": f"Alert rule {rule.name} deleted"}


class ScheduleCreate(BaseModel):
    container_id: str
    action: str
    time: str  # HH:MM format

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


@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    container_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import Schedule
    
    query = db.query(Schedule)
    if container_id:
        query = query.filter(Schedule.container_id == container_id)
    
    schedules = query.all()
    containers = db.query(Container).all()
    container_map = {c.id: c.name for c in containers}
    
    return [
        ScheduleResponse(
            id=s.id,
            container_id=s.container_id,
            container_name=container_map.get(s.container_id),
            action=s.action,
            time=s.time,
            enabled=bool(s.enabled),
            created_at=s.created_at
        )
        for s in schedules
    ]


@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import Schedule
    
    container = db.query(Container).filter(Container.id == schedule_data.container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    if schedule_data.action not in ["start", "stop", "restart"]:
        raise HTTPException(status_code=400, detail="Action must be start, stop, or restart")
    
    schedule = Schedule(
        container_id=schedule_data.container_id,
        action=schedule_data.action,
        time=schedule_data.time,
        enabled=1
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return ScheduleResponse(
        id=schedule.id,
        container_id=schedule.container_id,
        container_name=container.name,
        action=schedule.action,
        time=schedule.time,
        enabled=bool(schedule.enabled),
        created_at=schedule.created_at
    )


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import Schedule
    
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if schedule_data.action is not None:
        if schedule_data.action not in ["start", "stop", "restart"]:
            raise HTTPException(status_code=400, detail="Action must be start, stop, or restart")
        schedule.action = schedule_data.action
    if schedule_data.time is not None:
        schedule.time = schedule_data.time
    if schedule_data.enabled is not None:
        schedule.enabled = 1 if schedule_data.enabled else 0
    
    db.commit()
    db.refresh(schedule)
    
    container = db.query(Container).filter(Container.id == schedule.container_id).first()
    
    return ScheduleResponse(
        id=schedule.id,
        container_id=schedule.container_id,
        container_name=container.name if container else None,
        action=schedule.action,
        time=schedule.time,
        enabled=bool(schedule.enabled),
        created_at=schedule.created_at
    )


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import Schedule
    
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    
    return {"status": "success", "message": "Schedule deleted"}


class ExecCreate(BaseModel):
    cmd: List[str]
    tty: bool = True
    stdin: bool = False


@router.post("/containers/{container_id}/exec")
async def create_exec(
    container_id: str,
    exec_data: ExecCreate,
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer role cannot execute commands"
        )
    
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    result = monitor.exec_in_container(
        container_id,
        exec_data.cmd,
        exec_data.tty,
        exec_data.stdin
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create exec session")
    
    return result
