"""
Docker resources API endpoints (images, volumes, networks)
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.models import get_db, User
from app.core.security import get_current_user
from app.services.docker_client import get_docker_client_service
from app.core.exceptions import DockerAPIError, ValidationError
from app.core.validation import validate_string

router = APIRouter(prefix="/docker", tags=["docker-resources"])


# ==================== IMAGES ====================


@router.get("/images")
async def list_images(
    all_images: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Docker images"""
    try:
        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        images = docker.images.list(all=all_images)

        return [
            {
                "id": img.id,
                "tags": img.tags or [],
                "size": img.attrs.get("Size", 0),
                "created": img.attrs.get("Created", ""),
                "labels": img.attrs.get("Config", {}).get("Labels", {}) or {},
            }
            for img in images
        ]
    except Exception as e:
        raise DockerAPIError(f"Failed to list images: {str(e)}")


@router.post("/images/pull")
async def pull_image(
    image_name: str,
    tag: str = "latest",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pull a Docker image"""
    try:
        image_name = validate_string(image_name, "image_name", max_length=100)
        tag = validate_string(tag, "tag", max_length=50)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client

        # Pull in background if requested
        if background_tasks:
            background_tasks.add_task(docker.images.pull, f"{image_name}:{tag}")
            return {
                "status": "pending",
                "message": f"Pulling {image_name}:{tag} in background",
            }

        # Pull synchronously
        image = docker.images.pull(f"{image_name}:{tag}")
        return {
            "status": "success",
            "message": f"Successfully pulled {image_name}:{tag}",
            "image_id": image.id,
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to pull image: {str(e)}")


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Docker image"""
    try:
        image_id = validate_string(image_id, "image_id", max_length=100)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        image = docker.images.get(image_id)
        docker.images.remove(image.id, force=force)

        return {"status": "success", "message": f"Image {image_id} deleted"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to delete image: {str(e)}")


@router.post("/images/{image_id}/tag")
async def tag_image(
    image_id: str,
    tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tag a Docker image"""
    try:
        image_id = validate_string(image_id, "image_id", max_length=100)
        tag = validate_string(tag, "tag", max_length=100)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        image = docker.images.get(image_id)
        image.tag(tag)

        return {"status": "success", "message": f"Image tagged with {tag}"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to tag image: {str(e)}")


# ==================== IMAGE HISTORY ====================


@router.get("/images/{image_id}/history")
async def get_image_history(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get image history/layers"""
    try:
        image_id = validate_string(image_id, "image_id", max_length=100)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client

        image = docker.images.get(image_id)
        history = image.history()

        return [
            {
                "id": h.get("Id", ""),
                "created": h.get("Created", ""),
                "created_by": h.get("CreatedBy", ""),
                "size": h.get("Size", 0),
                "comment": h.get("Comment", ""),
            }
            for h in history
        ]
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to get image history: {str(e)}")


# ==================== VOLUMES ====================


@router.get("/volumes")
async def list_volumes(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List Docker volumes"""
    try:
        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        volumes = docker.volumes.list()

        return [
            {
                "name": vol.name,
                "driver": vol.attrs.get("Driver", "local"),
                "mountpoint": vol.attrs.get("Mountpoint", ""),
                "created": vol.attrs.get("CreatedAt", ""),
                "labels": vol.attrs.get("Labels", {}) or {},
                "size": vol.attrs.get("UsageData", {}).get("Size", 0)
                if vol.attrs.get("UsageData")
                else 0,
            }
            for vol in volumes
        ]
    except Exception as e:
        raise DockerAPIError(f"Failed to list volumes: {str(e)}")


@router.post("/volumes")
async def create_volume(
    name: str,
    driver: str = "local",
    labels: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Docker volume"""
    try:
        name = validate_string(name, "name", max_length=100)
        driver = validate_string(driver, "driver", max_length=50)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        volume = docker.volumes.create(name=name, driver=driver, labels=labels or {})

        return {
            "status": "success",
            "message": f"Volume {name} created",
            "volume": {
                "name": volume.name,
                "driver": volume.attrs.get("Driver", "local"),
                "mountpoint": volume.attrs.get("Mountpoint", ""),
            },
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to create volume: {str(e)}")


@router.delete("/volumes/{name}")
async def delete_volume(
    name: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Docker volume"""
    try:
        name = validate_string(name, "name", max_length=100)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        volume = docker.volumes.get(name)
        volume.remove(force=force)

        return {"status": "success", "message": f"Volume {name} deleted"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to delete volume: {str(e)}")


# ==================== NETWORKS ====================


@router.get("/networks")
async def list_networks(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List Docker networks"""
    try:
        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        networks = docker.networks.list()

        return [
            {
                "id": net.id,
                "name": net.name,
                "driver": net.attrs.get("Driver", "bridge"),
                "scope": net.attrs.get("Scope", "local"),
                "created": net.attrs.get("Created", ""),
                "labels": net.attrs.get("Labels", {}) or {},
                "internal": net.attrs.get("Internal", False),
                "attachable": net.attrs.get("Attachable", False),
                "ingress": net.attrs.get("Ingress", False),
                "containers": list(net.attrs.get("Containers", {}).keys())
                if net.attrs.get("Containers")
                else [],
            }
            for net in networks
        ]
    except Exception as e:
        raise DockerAPIError(f"Failed to list networks: {str(e)}")


@router.post("/networks")
async def create_network(
    name: str,
    driver: str = "bridge",
    internal: bool = False,
    attachable: bool = False,
    labels: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Docker network"""
    try:
        name = validate_string(name, "name", max_length=100)
        driver = validate_string(driver, "driver", max_length=50)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        network = docker.networks.create(
            name=name,
            driver=driver,
            internal=internal,
            attachable=attachable,
            labels=labels or {},
        )

        return {
            "status": "success",
            "message": f"Network {name} created",
            "network": {"id": network.id, "name": network.name, "driver": driver},
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to create network: {str(e)}")


@router.delete("/networks/{network_id}")
async def delete_network(
    network_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Docker network"""
    try:
        network_id = validate_string(network_id, "network_id", max_length=100)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        network = docker.networks.get(network_id)
        network.remove()

        return {"status": "success", "message": f"Network {network_id} deleted"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to delete network: {str(e)}")
