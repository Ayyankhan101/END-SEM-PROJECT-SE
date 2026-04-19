"""
Backup and restore API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import shutil
import os
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from app.db.models import get_db, User, Container, Metric, Alert, Stack, Host, Settings
from app.core.security import get_current_user
from app.core.config import get_config
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/backup", tags=["backup"])

# Use project data directory for backups
_base_dir = Path(__file__).parent.parent.parent
BACKUP_DIR = _base_dir / "data" / "backups"


def ensure_backup_dir():
    """Ensure backup directory exists"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/list")
@limiter.limit("30/minute")
async def list_backups(
    request: Request,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List available backups"""
    ensure_backup_dir()

    backups = []
    for backup_file in BACKUP_DIR.glob("dockwatch_backup_*.tar.gz"):
        stat = backup_file.stat()
        backups.append(
            {
                "filename": backup_file.name,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(backup_file),
            }
        )

    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x["created"], reverse=True)

    return {"backups": backups}


@router.post("/create")
@limiter.limit("5/minute")
async def create_backup(
    request: Request,
    background_tasks: BackgroundTasks,
    include_metrics: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new backup"""
    ensure_backup_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dockwatch_backup_{timestamp}.tar.gz"
    backup_path = BACKUP_DIR / filename

    # Create backup in background
    background_tasks.add_task(create_backup_archive, backup_path, include_metrics, db)

    return {
        "status": "pending",
        "message": "Backup creation started",
        "filename": filename,
    }


def create_backup_archive(backup_path: Path, include_metrics: bool, db: Session):
    """Create backup archive"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Export database data
            data = {
                "containers": [],
                "stacks": [],
                "hosts": [],
                "settings": {},
                "backup_metadata": {
                    "version": "1.0",
                    "created": datetime.now().isoformat(),
                    "include_metrics": include_metrics,
                },
            }

            # Export containers
            containers = db.query(Container).all()
            for c in containers:
                container_data = {
                    "id": c.id,
                    "name": c.name,
                    "image": c.image,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "last_updated": c.last_updated.isoformat()
                    if c.last_updated
                    else None,
                }

                if include_metrics:
                    metrics = db.query(Metric).filter(Metric.container_id == c.id).all()
                    container_data["metrics"] = [
                        {
                            "cpu_percent": m.cpu_percent,
                            "memory_percent": m.memory_percent,
                            "memory_usage": m.memory_usage,
                            "timestamp": m.timestamp.isoformat()
                            if m.timestamp
                            else None,
                        }
                        for m in metrics
                    ]

                data["containers"].append(container_data)

            # Export stacks
            stacks = db.query(Stack).all()
            for s in stacks:
                data["stacks"].append(
                    {
                        "id": s.id,
                        "name": s.name,
                        "compose_file": s.compose_file,
                        "status": s.status,
                        "created_at": s.created_at.isoformat()
                        if s.created_at
                        else None,
                        "updated_at": s.updated_at.isoformat()
                        if s.updated_at
                        else None,
                    }
                )

            # Export hosts
            hosts = db.query(Host).all()
            for h in hosts:
                data["hosts"].append(
                    {
                        "id": h.id,
                        "name": h.name,
                        "socket_path": h.socket_path,
                        "api_version": h.api_version,
                        "status": h.status,
                        "last_seen": h.last_seen.isoformat() if h.last_seen else None,
                    }
                )

            # Write data to temp file
            data_file = temp_path / "data.json"
            import json

            with open(data_file, "w") as f:
                json.dump(data, f, indent=2)

            # Create tar.gz archive
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(data_file, arcname="data.json")

                # Also backup config file if it exists
                config = get_config()
                config_path = (
                    Path(config.database.path).parent.parent / "config" / "config.yaml"
                )
                if config_path.exists():
                    tar.add(config_path, arcname="config.yaml")

    except Exception as e:
        # Clean up on failure
        if backup_path.exists():
            backup_path.unlink()
        raise e


@router.post("/restore")
@limiter.limit("2/minute")
async def restore_backup(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restore from backup"""
    if not file.filename.endswith(".tar.gz"):
        raise HTTPException(
            status_code=400, detail="Invalid file format. Expected .tar.gz"
        )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save uploaded file
            backup_path = temp_path / "backup.tar.gz"
            with open(backup_path, "wb") as f:
                content = await file.read()
                f.write(content)

            # Extract archive
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_path)

            # Load data
            data_file = temp_path / "data.json"
            with open(data_file, "r") as f:
                import json

                data = json.load(f)

            # Restore containers
            for container_data in data.get("containers", []):
                existing = (
                    db.query(Container)
                    .filter(Container.id == container_data["id"])
                    .first()
                )
                if not existing:
                    container = Container(
                        id=container_data["id"],
                        name=container_data["name"],
                        image=container_data.get("image"),
                        status=container_data.get("status", "unknown"),
                    )
                    db.add(container)

            # Restore stacks
            for stack_data in data.get("stacks", []):
                existing = db.query(Stack).filter(Stack.id == stack_data["id"]).first()
                if not existing:
                    stack = Stack(
                        id=stack_data["id"],
                        name=stack_data["name"],
                        compose_file=stack_data["compose_file"],
                        status=stack_data.get("status", "stopped"),
                    )
                    db.add(stack)

            # Restore hosts
            for host_data in data.get("hosts", []):
                existing = db.query(Host).filter(Host.id == host_data["id"]).first()
                if not existing:
                    host = Host(
                        id=host_data["id"],
                        name=host_data["name"],
                        socket_path=host_data.get(
                            "socket_path", "unix:///var/run/docker.sock"
                        ),
                        api_version=host_data.get("api_version", "1.41"),
                        status=host_data.get("status", "disconnected"),
                    )
                    db.add(host)

            db.commit()

            return {
                "status": "success",
                "message": "Backup restored successfully",
                "restored": {
                    "containers": len(data.get("containers", [])),
                    "stacks": len(data.get("stacks", [])),
                    "hosts": len(data.get("hosts", [])),
                },
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to restore backup: {str(e)}"
        )
