"""
Trivy CVE Scanner API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trivy", tags=["security"])


def ensure_docker_connected(monitor):
    """Ensure Docker monitor is connected."""
    if not hasattr(monitor, '_container_service') or monitor._container_service is None:
        if not monitor.connect():
            raise HTTPException(
                status_code=500, 
                detail="Failed to connect to Docker daemon. Is Docker running?"
            )


@router.get("/scan/{container_id}")
async def scan_container_vulnerabilities(
    container_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Scan a container for vulnerabilities using Trivy."""
    from app.services.trivy_scanner import get_trivy_scanner
    
    scanner = get_trivy_scanner()
    result = scanner.scan_container(container_id)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/scan/image/{image_name:path}")
async def scan_image_vulnerabilities(
    image_name: str,
    current_user: dict = Depends(get_current_user),
):
    """Scan an image for vulnerabilities using Trivy."""
    from app.services.trivy_scanner import get_trivy_scanner
    
    scanner = get_trivy_scanner()
    result = scanner.scan_image(image_name)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/health")
async def trivy_health_check(current_user: dict = Depends(get_current_user)):
    """Check if Trivy is available."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "images", "aquasec/trivy:latest", "-q"],
            capture_output=True,
            text=True,
            timeout=10
        )
        # docker images returns code 0 even when image absent; image
        # present only if it prints an ID to stdout.
        available = result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        available = False
    
    return {
        "available": available,
        "image": "aquasec/trivy:latest",
        "description": "Trivy CVE scanner for container security"
    }