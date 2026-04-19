"""
Health check API endpoint
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import get_db
from app.services.docker_client import get_docker_client_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(db: Session = Depends(get_db)):
    """Basic health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with component status"""
    components = {"api": "healthy", "database": "unknown", "docker": "unknown"}
    overall_status = "healthy"

    # Check database
    try:
        db.execute("SELECT 1")
        components["database"] = "healthy"
    except Exception:
        components["database"] = "unhealthy"
        overall_status = "degraded"

    # Check Docker
    try:
        docker_service = get_docker_client_service()
        docker_service.connect()
        if docker_service.is_connected():
            components["docker"] = "healthy"
        else:
            components["docker"] = "disconnected"
            overall_status = "degraded"
    except Exception:
        components["docker"] = "unavailable"
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
    }


@router.get("/live")
async def liveness():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(db: Session = Depends(get_db)):
    """Readiness probe - checks if app can serve traffic"""
    try:
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Not ready")
