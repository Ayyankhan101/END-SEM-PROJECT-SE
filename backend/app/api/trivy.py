"""
Trivy CVE Scanner API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
import logging

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
):
    """Scan an image for vulnerabilities using Trivy."""
    from app.services.trivy_scanner import get_trivy_scanner
    
    scanner = get_trivy_scanner()
    result = scanner.scan_image(image_name)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/health")
async def trivy_health_check():
    """Check if Trivy is available."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "images", "aquasec/trivy:latest", "-q"],
            capture_output=True,
            timeout=10
        )
        available = result.returncode == 0
    except Exception:
        available = False
    
    return {
        "available": available,
        "image": "aquasec/trivy:latest",
        "description": "Trivy CVE scanner for container security"
    }