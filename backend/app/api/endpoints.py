from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


from app.api.utils import (
    check_container_ownership,
    check_resource_ownership,
    check_stack_ownership
)


class BulkContainerIds(BaseModel):
    container_ids: List[str]


def _bulk_container_operation(container_ids: List[str], db: Session, operation: str, current_user: dict) -> dict:
    """Generic bulk operation helper.
    
    Args:
        container_ids: List of container IDs
        db: Database session
        operation: One of 'start', 'stop', 'restart', 'delete'
        current_user: Authenticated user for ownership check
    
    Returns:
        dict with status and results
    """
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    results = []
    
    operation_map = {
        'start': lambda cid: monitor.restart_container(cid),  # restart works for stopped containers
        'stop': lambda cid: monitor.stop_container(cid),
        'restart': lambda cid: monitor.restart_container(cid),
        'delete': lambda cid: monitor.remove_container(cid),
    }
    
    if operation not in operation_map:
        raise HTTPException(status_code=400, detail=f"Invalid operation: {operation}")
    
    op_func = operation_map[operation]
    
    for container_id in container_ids:
        try:
            # Ownership check (raises 404/403 if unauthorized)
            container = check_container_ownership(db, container_id, current_user)
            success = op_func(container_id)
            if operation == 'delete' and success:
                db.delete(container)
                db.commit()
            results.append({"id": container_id, "success": success})
        except HTTPException as e:
            results.append({"id": container_id, "success": False, "error": e.detail})
        except Exception as e:
            logger.error(f"Bulk {operation} failed for {container_id}: {e}", exc_info=True)
            results.append({"id": container_id, "success": False, "error": str(e)})
    
    return {"status": "success", "results": results}


from app.db.models import get_db
from app.db.models import Container, Metric, Alert, RecoveryAction, Stack, Host, AlertRule, Schedule
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
    TOTPSetupResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
    ContainerUpdate,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ExecCreate,
)
from app.core.security import create_access_token, verify_password, get_current_user, get_password_hash, get_user_role, create_refresh_token, revoke_token, revoke_all_user_tokens
from app.core.config import get_config
from app.core.rate_limiter import limiter
from app.core.validation import (
    validate_container_id,
    validate_container_name,
    validate_image_name,
    validate_positive_int,
)
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status


def get_current_user_with_auth(current_user: dict = Depends(get_current_user)):
    """Get current user with additional authorization checks."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user


def require_admin(current_user: dict = Depends(get_current_user_with_auth)):
    """Require admin role."""
    user_role = current_user.get("role")
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


router = APIRouter()


@router.post("/auth/token")
@limiter.limit("10/minute")
async def login(
    request: Request, request_data: LoginRequest, db: Session = Depends(get_db)
):
    from app.db.models import User
    import pyotp

    user = db.query(User).filter(User.username == request_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Check lockout
    if user.lockout_until and user.lockout_until > datetime.utcnow():
        wait_seconds = int((user.lockout_until - datetime.utcnow()).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {wait_seconds} seconds.",
        )

    if not verify_password(request_data.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.lockout_until = datetime.utcnow() + timedelta(minutes=15)
            user.failed_login_attempts = 0
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Too many failed attempts. Account locked for 15 minutes.",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Reset failed attempts on success
    user.failed_login_attempts = 0
    user.lockout_until = None
    db.commit()
    
    # If password change required, return 403 with header
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password must be changed",
            headers={"X-Force-Password-Change": "true"}
        )
    
    if user.is_2fa_enabled and user.totp_secret:
        return TokenResponse(access_token="", requires_2fa=True, user_id=user.id)
    
    access_token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id}, fresh=True)
    refresh_token = create_refresh_token({"sub": user.username, "role": user.role, "user_id": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user_id=user.id)


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
    import json
    from app.core.security import decrypt_secret

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not configured")
    
    # Try TOTP verification first
    secret = decrypt_secret(user.totp_secret)
    if not secret:
        raise HTTPException(status_code=500, detail="Failed to decrypt 2FA secret")
        
    totp = pyotp.TOTP(secret)
    if totp.verify(code):
        access_token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id}, fresh=True)
        refresh_token = create_refresh_token({"sub": user.username, "role": user.role, "user_id": user.id})
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, user_id=user.id)

    # Try Backup Code verification
    if user.backup_codes:
        try:
            codes_json = decrypt_secret(user.backup_codes)
            backup_codes = json.loads(codes_json)
            if code in backup_codes:
                # Use code and remove it
                backup_codes.remove(code)
                user.backup_codes = encrypt_secret(json.dumps(backup_codes))
                db.commit()
                
                access_token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id}, fresh=True)
                refresh_token = create_refresh_token({"sub": user.username, "role": user.role, "user_id": user.id})
                return TokenResponse(access_token=access_token, refresh_token=refresh_token, user_id=user.id)
        except Exception as e:
            logger.error(f"Backup code check failed: {e}")

    raise HTTPException(status_code=401, detail="Invalid 2FA code")


@router.post("/auth/2fa/setup")
@limiter.limit("10/minute")
async def setup_2fa(
    request: Request,
    user_id: int,
    code: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import User
    import pyotp
    import qrcode
    import io
    import base64
    import secrets
    import string
    import json
    from app.core.security import encrypt_secret, decrypt_secret

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify code if provided (finalizing setup)
    if user.totp_secret and code:
        secret = decrypt_secret(user.totp_secret)
        if not secret:
             raise HTTPException(status_code=500, detail="Failed to decrypt 2FA secret")
             
        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            raise HTTPException(status_code=401, detail="Invalid verification code")
        
        # Generate backup codes
        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        user.backup_codes = encrypt_secret(json.dumps(codes))
        user.is_2fa_enabled = 1
        db.commit()
        return {"status": "success", "backup_codes": codes}
    
    # Generate new secret (initial step)
    secret = pyotp.random_base32()
    user.totp_secret = encrypt_secret(secret)
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
        from app.core.security import decrypt_secret
        secret = decrypt_secret(user.totp_secret)
        if not secret:
             raise HTTPException(status_code=500, detail="Failed to decrypt 2FA secret")
             
        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    user.totp_secret = None
    user.is_2fa_enabled = 0
    db.commit()
    
    return {"status": "success", "message": "2FA disabled"}


@router.post("/auth/refresh")
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        payload = verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        new_token = create_access_token({"sub": username, "role": user.role, "user_id": user.id}, fresh=False)
        return {"access_token": new_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/auth/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Logout and revoke current token."""
    from fastapi import Request as FastRequest
    # Extract token from header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        revoke_token(token)
    
    return {"status": "success", "message": "Logged out"}


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
    show_all: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Container)
    # Show all containers by default (matching AI Insights)
    # Set show_all=False to filter by user ownership
    if not show_all:
        if get_user_role(current_user) != "admin":
            user_id = current_user.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=403, detail="Invalid user")
            query = query.filter(Container.user_id == user_id)
    if favorites:
        query = query.filter(Container.is_favorite == 1)
    containers = query.all()
    return containers


@router.post("/containers/sync")
@limiter.limit("10/minute")
async def sync_containers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Manually sync Docker containers to database."""
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    monitor._sync_containers_to_db()
    
    return {"status": "success", "message": "Containers synced"}


@router.get("/containers/{container_id}", response_model=ContainerDetail)
@limiter.limit("60/minute")
async def get_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    container = check_container_ownership(db, validated_id, current_user)

    from app.services.docker_monitor import get_docker_monitor
    monitor = get_docker_monitor()
    docker_info = monitor.get_container(container_id)

    if docker_info:
        container.config = docker_info.get("config", {})
        container.network_settings = docker_info.get("network_settings", {})

    return container


@router.get("/containers/{container_id}/metrics")
@limiter.limit("60/minute")
async def get_container_metrics(
    request: Request,
    container_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    container = check_container_ownership(db, container_id, current_user)

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
@limiter.limit("60/minute")
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
        # Enforce ownership on specific container
        container = check_container_ownership(db, container_id, current_user)
        query = query.filter(Metric.container_id == container_id)
    else:
        # Filter metrics to only containers user owns
        if get_user_role(current_user) != "admin":
            user_id = current_user.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=403, detail="Invalid user")
            query = query.join(Container, Metric.container_id == Container.id).filter(Container.user_id == user_id)

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
@limiter.limit("60/minute")
async def get_alerts(
    request: Request,
    limit: int = 50,
    container_id: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Alert).order_by(Alert.timestamp.desc())

    if container_id:
        # Ensure user can access this container
        container = check_container_ownership(db, container_id, current_user)
        query = query.filter(Alert.container_id == container_id)
    else:
        # Restrict to user's own containers unless admin
        if get_user_role(current_user) != "admin":
            user_id = current_user.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=403, detail="Invalid user")
            query = query.join(Container, Alert.container_id == Container.id).filter(Container.user_id == user_id)

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
    
    # Ownership check
    check_container_ownership(db, container_id, current_user)

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


@router.post("/containers/{container_id}/start")
@limiter.limit("30/minute")
async def start_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor
    
    # Ownership check
    check_container_ownership(db, container_id, current_user)

    monitor = get_docker_monitor()
    success = monitor.start_container(container_id)

    if success:
        action = RecoveryAction(
            container_id=container_id, action_type="start", status="success"
        )
        db.add(action)
        db.commit()
        return {"status": "success", "message": f"Container {container_id} started"}
    else:
        action = RecoveryAction(
            container_id=container_id, action_type="start", status="failed"
        )
        db.add(action)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to start container")


@router.post("/containers/{container_id}/pause")
@limiter.limit("30/minute")
async def pause_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor
    
    # Ownership check
    check_container_ownership(db, container_id, current_user)

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
    
    # Ownership check
    check_container_ownership(db, container_id, current_user)

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
    
    # Ownership check
    check_container_ownership(db, container_id, current_user)

    monitor = get_docker_monitor()
    success = monitor.stop_container(container_id)

    if success:
        action = RecoveryAction(
            container_id=container_id, action_type="stop", status="success"
        )
        db.add(action)
        db.commit()
        return {"status": "success", "message": f"Container {container_id} stopped"}
    else:
        action = RecoveryAction(
            container_id=container_id, action_type="stop", status="failed"
        )
        db.add(action)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to stop container")


@router.get("/containers/{container_id}/logs")
@limiter.limit("60/minute")
async def get_container_logs(
    request: Request,
    container_id: str,
    lines: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor

    container = check_container_ownership(db, container_id, current_user)

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
        user_id=current_user.get("user_id"),
    )
    db.add(container)
    db.commit()

    return {"status": "success", "container": result}


@router.get("/stacks", response_model=List[StackResponse])
@limiter.limit("60/minute")
async def list_stacks(
    request: Request,
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    query = db.query(Stack)
    if get_user_role(current_user) != "admin":
        user_id = current_user.get("user_id")
        query = query.filter(Stack.user_id == user_id)
    
    stacks = query.order_by(Stack.created_at.desc()).all()
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
    
    # Deploy to Docker
    success = monitor.deploy_stack(stack.name, stack.compose_file)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to deploy stack")

    # Save to DB with ownership
    new_stack = Stack(
        name=stack.name,
        compose_file=stack.compose_file,
        user_id=current_user.get("user_id"),
        status="running"
    )
    db.add(new_stack)
    db.commit()
    db.refresh(new_stack)
    
    return new_stack


@router.delete("/stacks/{stack_id}")
@limiter.limit("20/minute")
async def delete_stack(
    request: Request,
    stack_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor
    
    # Ownership check
    stack = check_stack_ownership(db, stack_id, current_user)
    
    # Remove from Docker
    monitor = get_docker_monitor()
    monitor.stop_stack(stack.name)
    
    # Delete from DB
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
@limiter.limit("60/minute")
async def list_hosts(
    request: Request,
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
@limiter.limit("30/minute")
async def delete_host(
    request: Request,
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
@limiter.limit("60/minute")
async def get_settings(
    request: Request,
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
@limiter.limit("30/minute")
async def bulk_start_containers(
    request: Request,
    body: BulkContainerIds,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for bulk start"
        )
    return _bulk_container_operation(body.container_ids, db, 'start', current_user)


@router.post("/containers/bulk/stop")
@limiter.limit("30/minute")
async def bulk_stop_containers(
    request: Request,
    body: BulkContainerIds,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for bulk stop"
        )
    return _bulk_container_operation(body.container_ids, db, 'stop', current_user)


@router.post("/containers/bulk/restart")
@limiter.limit("30/minute")
async def bulk_restart_containers(
    request: Request,
    body: BulkContainerIds,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = get_user_role(current_user)
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for bulk restart"
        )
    return _bulk_container_operation(body.container_ids, db, 'restart', current_user)


@router.post("/containers/bulk/delete")
@limiter.limit("30/minute")
async def bulk_delete_containers(
    request: Request,
    body: BulkContainerIds,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # _bulk_container_operation already handles ownership checks
    return _bulk_container_operation(body.container_ids, db, 'delete', current_user)


@router.delete("/containers/{container_id}")
@limiter.limit("30/minute")
async def delete_container(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.docker_monitor import get_docker_monitor
    
    # Ownership check
    container = check_container_ownership(db, container_id, current_user)

    monitor = get_docker_monitor()
    success = monitor.remove_container(container_id)

    if success:
        # Delete from DB
        db.delete(container)
        db.commit()
        
        # Notify via WebSocket
        from app.api.websocket import websocket_callback
        websocket_callback({
            "type": "container_deleted",
            "container_id": container_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {"status": "success", "message": f"Container {container_id} deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete container")


@router.post("/containers/{container_id}/favorite")
@limiter.limit("60/minute")
async def toggle_container_favorite(
    request: Request,
    container_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    container = check_container_ownership(db, validated_id, current_user)

    container.is_favorite = 1 if container.is_favorite != 1 else 0
    db.commit()

    return {
        "status": "success",
        "is_favorite": container.is_favorite,
        "message": f"Container {container_id} favorite toggled"
    }


@router.put("/containers/{container_id}/env")
@limiter.limit("30/minute")
async def update_container_env(
    request: Request,
    container_id: str,
    env_vars: Dict[str, str],
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    container = check_container_ownership(db, validated_id, current_user)
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    success = monitor.update_container_env(validated_id, env_vars)

    if success:
        return {"status": "success", "message": "Environment updated"}
    raise HTTPException(status_code=500, detail="Failed to update environment")


@router.put("/containers/{container_id}/ports")
@limiter.limit("30/minute")
async def update_container_ports(
    request: Request,
    container_id: str,
    ports: Dict[str, int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    container = check_container_ownership(db, validated_id, current_user)
    from app.services.docker_monitor import get_docker_monitor

    monitor = get_docker_monitor()
    success = monitor.update_container_ports(validated_id, ports)

    if success:
        return {"status": "success", "message": "Ports updated"}
    raise HTTPException(status_code=500, detail="Failed to update ports")


@router.put("/containers/{container_id}", response_model=ContainerResponse)
@limiter.limit("30/minute")
async def update_container(
    request: Request,
    container_id: str,
    container_data: ContainerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    validated_id = validate_container_id(container_id)
    container = check_container_ownership(db, validated_id, current_user)

    if container_data.group is not None:
        container.group = container_data.group

    db.commit()
    db.refresh(container)
    return container


@router.get("/containers/group/{group}", response_model=List[ContainerResponse])
@limiter.limit("60/minute")
async def list_containers_by_group(
    request: Request,
    group: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = db.query(Container).filter(Container.group == group)
    # Restrict to user's containers unless admin
    if get_user_role(current_user) != "admin":
        user_id = current_user.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=403, detail="Invalid user")
        query = query.filter(Container.user_id == user_id)
    containers = query.all()
    return containers


@router.get("/users", response_model=List[UserResponse])
@limiter.limit("60/minute")
async def list_users(
    request: Request,
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
        )
        for u in users
    ]


@router.post("/users", response_model=UserResponse)
@limiter.limit("30/minute")
async def create_user(
    request: Request,
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role or "user",
        created_at=user.created_at,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
@limiter.limit("30/minute")
async def update_user(
    request: Request,
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
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role or "user",
        created_at=user.created_at,
    )


@router.delete("/users/{user_id}")
@limiter.limit("30/minute")
async def delete_user(
    request: Request,
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


@router.get("/alert-rules", response_model=List[AlertRuleResponse])
@limiter.limit("60/minute")
async def list_alert_rules(
    request: Request,
    container_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import AlertRule

    query = db.query(AlertRule)
    if container_id:
        # Verify ownership of container
        container = check_container_ownership(db, container_id, current_user)
        query = query.filter(AlertRule.container_id == container_id)
    else:
        # Restrict to rules for user's containers or global
        if get_user_role(current_user) != "admin":
            user_id = current_user.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=403, detail="Invalid user")
            user_container_ids = db.query(Container.id).filter(Container.user_id == user_id).subquery()
            query = query.filter(
                (AlertRule.container_id.is_(None)) |
                (AlertRule.container_id.in_(db.query(Container.id).filter(Container.user_id == user_id)))
            )

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
@limiter.limit("30/minute")
async def create_alert_rule(
    request: Request,
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

    # If container_id provided, ensure user owns that container
    if rule_data.container_id:
        container = check_container_ownership(db, rule_data.container_id, current_user)

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
@limiter.limit("30/minute")
async def update_alert_rule(
    request: Request,
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

    # If rule targets a container, verify ownership
    if rule.container_id:
        container = check_container_ownership(db, rule.container_id, current_user)

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
@limiter.limit("30/minute")
async def delete_alert_rule(
    request: Request,
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


@router.get("/schedules", response_model=List[ScheduleResponse])
@limiter.limit("60/minute")
async def list_schedules(
    request: Request,
    container_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import Schedule

    query = db.query(Schedule)
    if container_id:
        # Verify ownership of the specified container
        container = check_container_ownership(db, container_id, current_user)
        query = query.filter(Schedule.container_id == container_id)
    else:
        # Restrict to schedules of user's containers (unless admin)
        if get_user_role(current_user) != "admin":
            user_id = current_user.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=403, detail="Invalid user")
            query = query.join(Container, Schedule.container_id == Container.id).filter(Container.user_id == user_id)

    schedules = query.all()
    # Build container name map only for containers user can see (filtered)
    container_ids = [s.container_id for s in schedules]
    containers = db.query(Container).filter(Container.id.in_(container_ids)).all()
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
@limiter.limit("30/minute")
async def create_schedule(
    request: Request,
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
@limiter.limit("30/minute")
async def update_schedule(
    request: Request,
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import Schedule

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Verify user owns the container this schedule belongs to
    container = check_container_ownership(db, schedule.container_id, current_user)

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

    return ScheduleResponse(
        id=schedule.id,
        container_id=schedule.container_id,
        container_name=container.name,
        action=schedule.action,
        time=schedule.time,
        enabled=bool(schedule.enabled),
        created_at=schedule.created_at
    )


@router.delete("/schedules/{schedule_id}")
@limiter.limit("30/minute")
async def delete_schedule(
    request: Request,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.db.models import Schedule

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Ensure user owns the container this schedule belongs to
    container = check_container_ownership(db, schedule.container_id, current_user)

    db.delete(schedule)
    db.commit()

    return {"status": "success", "message": "Schedule deleted"}


@router.post("/containers/{container_id}/exec")
@limiter.limit("30/minute")
async def create_exec(
    request: Request,
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


@router.post("/auth/change-password")
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Change user password."""
    from app.db.models import User
    import re

    # Validate password strength
    if len(new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters long"
        )
    if not re.search(r'[A-Z]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain uppercase letter"
        )
    if not re.search(r'[a-z]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain lowercase letter"
        )
    if not re.search(r'[0-9]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain digit"
        )
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain special character"
        )

    username = current_user.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect old password"
        )
    
    if old_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from old password"
        )
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Revoke all tokens for user
    revoke_all_user_tokens(username)
    
    return {"status": "success", "message": "Password changed successfully"}


@router.post("/auth/force-change-password")
@limiter.limit("10/minute")
async def force_change_password(
    request: Request,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Force password change (for first login or admin requirement)."""
    from app.db.models import User
    import re

    username = current_user.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate password strength
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    if not re.search(r'[A-Z]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain uppercase letter"
        )
    if not re.search(r'[a-z]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain lowercase letter"
        )
    if not re.search(r'[0-9]', new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain digit"
        )
    
    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = 0
    user.force_password_change = 0
    db.commit()
    
    return {"status": "success", "message": "Password changed successfully"}


from pydantic import BaseModel

class PasswordChangeFirstLoginRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

@router.post("/auth/change-password-first-login")
@limiter.limit("10/minute")
async def change_password_first_login(
    request: Request,
    request_data: PasswordChangeFirstLoginRequest,
    db: Session = Depends(get_db)
):
    """Change password for first login - no authentication required."""
    from app.db.models import User
    import re

    # Validate input
    if not request_data.username or not request_data.old_password or not request_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username, old password, and new password are required"
        )
    
    # Find user
    user = db.query(User).filter(User.username == request_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username or password"
        )
    
    # Verify old password
    if not verify_password(request_data.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username or password"
        )
    
    # Validate password strength
    if len(request_data.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters long"
        )
    if not re.search(r'[A-Z]', request_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain uppercase letter"
        )
    if not re.search(r'[a-z]', request_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain lowercase letter"
        )
    if not re.search(r'[0-9]', request_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain digit"
        )
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', request_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain special character"
        )
    
    # Check if new password is different from old
    if request_data.old_password == request_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from old password"
        )
    
    # Update password 
    user.hashed_password = get_password_hash(request_data.new_password)
    db.commit()
    
    # Revoke all existing tokens for this user
    revoke_all_user_tokens(request_data.username)
    
    return {"status": "success", "message": "Password changed successfully"}
