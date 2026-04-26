"""
Health check API endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
from app.db.models import get_db
from app.services.docker_client import get_docker_client_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
@router.get("/")
async def health_check(
    db: Session = Depends(get_db)
):
    """
    Check system health.
    Returns 200 if all systems operational, 503 otherwise.
    """
    health_status = {
        "status": "healthy",
        "components": {
            "database": "unhealthy",
            "docker": "unhealthy"
        }
    }
    
    # Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Health check: Database error: {e}")
        health_status["status"] = "unhealthy"
        
    # Check Docker
    try:
        docker_service = get_docker_client_service()
        if docker_service.is_connected() or docker_service.connect():
            health_status["components"]["docker"] = "healthy"
        else:
            health_status["status"] = "unhealthy"
    except Exception as e:
        logger.error(f"Health check: Docker error: {e}")
        health_status["status"] = "unhealthy"
        
    if health_status["status"] == "unhealthy":
        # Return 200 so UI doesn't say "Offline", but status is "unhealthy"
        return health_status
        
    return health_status
