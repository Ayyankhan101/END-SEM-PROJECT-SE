"""
Docker resources API endpoints (images, volumes, networks)
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.models import get_db, User, DockerResource, RegistryCredential
from app.core.security import get_current_user, encrypt_secret, decrypt_secret
from app.services.docker_client import get_docker_client_service
from app.core.exceptions import DockerAPIError, ValidationError
from app.core.validation import validate_string
from app.core.rate_limiter import limiter
from app.api.utils import check_resource_ownership

router = APIRouter(prefix="/docker", tags=["docker-resources"])


# ==================== IMAGES ====================


@router.get("/images")
@limiter.limit("60/minute")
async def list_images(
    request: Request,
    all_images: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List Docker images with filtering for owned resources."""
    try:
        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        images = docker.images.list(all=all_images)

        # Get owned image IDs if not admin
        owned_ids = []
        is_admin = current_user.get("role") == "admin"
        if not is_admin:
            owned_ids = [r.resource_id for r in db.query(DockerResource).filter(
                DockerResource.resource_type == "image",
                DockerResource.user_id == current_user.get("user_id")
            ).all()]

        result = []
        for img in images:
            # Filter: admin sees all, users see what they own
            if is_admin or img.id in owned_ids:
                result.append({
                    "id": img.id,
                    "tags": img.tags or [],
                    "size": img.attrs.get("Size", 0),
                    "created": img.attrs.get("Created", ""),
                    "labels": img.attrs.get("Config", {}).get("Labels", {}) or {},
                })
        
        return result
    except Exception as e:
        raise DockerAPIError(f"Failed to list images: {str(e)}")


@router.post("/images/pull")
@limiter.limit("10/minute")
async def pull_image(
    request: Request,
    image_name: str,
    tag: str = "latest",
    server_url: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Pull a Docker image and record ownership, supporting private registries."""
    try:
        image_name = validate_string(image_name, "image_name", max_length=100)
        tag = validate_string(tag, "tag", max_length=50)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client

        # Get credentials if server_url provided
        auth_config = None
        if server_url:
            cred = db.query(RegistryCredential).filter(
                RegistryCredential.server_url == server_url,
                RegistryCredential.user_id == current_user.get("user_id")
            ).first()
            if cred:
                auth_config = {
                    "username": cred.username,
                    "password": decrypt_secret(cred.password)
                }

        # Internal helper to record ownership
        def _record_image_ownership(img_id: str):
            resource = DockerResource(
                resource_type="image",
                resource_id=img_id,
                user_id=current_user.get("user_id")
            )
            db.add(resource)
            db.commit()

        full_image = f"{image_name}:{tag}"

        # Pull in background if requested
        if background_tasks:
            # We need to wrap it to record ownership after pull
            async def _pull_and_record():
                img = docker.images.pull(full_image, auth_config=auth_config)
                _record_image_ownership(img.id)
            
            background_tasks.add_task(_pull_and_record)
            return {
                "status": "pending",
                "message": f"Pulling {full_image} in background",
            }

        # Pull synchronously
        image = docker.images.pull(full_image, auth_config=auth_config)
        _record_image_ownership(image.id)
        
        return {
            "status": "success",
            "message": f"Successfully pulled {full_image}",
            "image_id": image.id,
        }
    except Exception as e:
        raise DockerAPIError(f"Failed to pull image: {str(e)}")


# ==================== REGISTRY CREDENTIALS ====================

@router.get("/credentials")
async def list_credentials(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List stored registry credentials (without passwords)."""
    creds = db.query(RegistryCredential).filter(
        RegistryCredential.user_id == current_user.get("user_id")
    ).all()
    return [
        {
            "id": c.id,
            "server_url": c.server_url,
            "username": c.username,
            "created_at": c.created_at
        }
        for c in creds
    ]

@router.post("/credentials")
async def add_credential(
    server_url: str,
    username: str,
    password: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Store encrypted registry credentials."""
    # Check if exists
    existing = db.query(RegistryCredential).filter(
        RegistryCredential.server_url == server_url,
        RegistryCredential.user_id == current_user.get("user_id")
    ).first()
    
    if existing:
        existing.username = username
        existing.password = encrypt_secret(password)
    else:
        new_cred = RegistryCredential(
            server_url=server_url,
            username=username,
            password=encrypt_secret(password),
            user_id=current_user.get("user_id")
        )
        db.add(new_cred)
    
    db.commit()
    return {"status": "success", "message": f"Credentials for {server_url} saved"}

@router.delete("/credentials/{cred_id}")
async def delete_credential(
    cred_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete stored registry credentials."""
    cred = db.query(RegistryCredential).filter(
        RegistryCredential.id == cred_id,
        RegistryCredential.user_id == current_user.get("user_id")
    ).first()
    
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    db.delete(cred)
    db.commit()
    return {"status": "success", "message": "Credential removed"}


@router.delete("/images/{image_id}")
@limiter.limit("20/minute")
async def delete_image(
    request: Request,
    image_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a Docker image with ownership check."""
    try:
        image_id = validate_string(image_id, "image_id", max_length=100)
        
        # Check ownership
        check_resource_ownership(db, "image", image_id, current_user)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        image = docker.images.get(image_id)
        docker.images.remove(image.id, force=force)

        # Cleanup ownership record
        db.query(DockerResource).filter(
            DockerResource.resource_type == "image",
            DockerResource.resource_id == image.id
        ).delete()
        db.commit()

        return {"status": "success", "message": f"Image {image_id} deleted"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to delete image: {str(e)}")


@router.post("/images/{image_id}/tag")
@limiter.limit("10/minute")
async def tag_image(
    request: Request,
    image_id: str,
    tag: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Tag a Docker image with ownership check."""
    try:
        image_id = validate_string(image_id, "image_id", max_length=100)
        tag = validate_string(tag, "tag", max_length=100)
        
        # Check ownership
        check_resource_ownership(db, "image", image_id, current_user)

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
@limiter.limit("30/minute")
async def get_image_history(
    request: Request,
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
@limiter.limit("60/minute")
async def list_volumes(
    request: Request,
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """List Docker volumes with ownership filtering."""
    try:
        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        volumes = docker.volumes.list()

        # Filter by ownership if not admin
        is_admin = current_user.get("role") == "admin"
        owned_names = []
        if not is_admin:
            owned_names = [r.resource_id for r in db.query(DockerResource).filter(
                DockerResource.resource_type == "volume",
                DockerResource.user_id == current_user.get("user_id")
            ).all()]

        result = []
        for vol in volumes:
            if is_admin or vol.name in owned_names:
                result.append({
                    "name": vol.name,
                    "driver": vol.attrs.get("Driver", "local"),
                    "mountpoint": vol.attrs.get("Mountpoint", ""),
                    "created": vol.attrs.get("CreatedAt", ""),
                    "labels": vol.attrs.get("Labels", {}) or {},
                    "size": vol.attrs.get("UsageData", {}).get("Size", 0)
                    if vol.attrs.get("UsageData")
                    else 0,
                })
        return result
    except Exception as e:
        raise DockerAPIError(f"Failed to list volumes: {str(e)}")


@router.post("/volumes")
@limiter.limit("10/minute")
async def create_volume(
    request: Request,
    name: str,
    driver: str = "local",
    labels: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a Docker volume and record ownership."""
    try:
        name = validate_string(name, "name", max_length=100)
        driver = validate_string(driver, "driver", max_length=50)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        volume = docker.volumes.create(name=name, driver=driver, labels=labels or {})

        # Record ownership
        resource = DockerResource(
            resource_type="volume",
            resource_id=volume.name,
            user_id=current_user.get("user_id")
        )
        db.add(resource)
        db.commit()

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
@limiter.limit("20/minute")
async def delete_volume(
    request: Request,
    name: str,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a Docker volume with ownership check."""
    try:
        name = validate_string(name, "name", max_length=100)
        
        # Check ownership
        check_resource_ownership(db, "volume", name, current_user)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        volume = docker.volumes.get(name)
        volume.remove(force=force)

        # Cleanup ownership record
        db.query(DockerResource).filter(
            DockerResource.resource_type == "volume",
            DockerResource.resource_id == name
        ).delete()
        db.commit()

        return {"status": "success", "message": f"Volume {name} deleted"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to delete volume: {str(e)}")


# ==================== NETWORKS ====================


@router.get("/networks")
@limiter.limit("60/minute")
async def list_networks(
    request: Request,
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """List Docker networks with ownership filtering."""
    try:
        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        networks = docker.networks.list()

        # Filter by ownership if not admin
        is_admin = current_user.get("role") == "admin"
        owned_ids = []
        if not is_admin:
            owned_ids = [r.resource_id for r in db.query(DockerResource).filter(
                DockerResource.resource_type == "network",
                DockerResource.user_id == current_user.get("user_id")
            ).all()]

        result = []
        for net in networks:
            if is_admin or net.id in owned_ids:
                result.append({
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
                })
        return result
    except Exception as e:
        raise DockerAPIError(f"Failed to list networks: {str(e)}")


@router.post("/networks")
@limiter.limit("10/minute")
async def create_network(
    request: Request,
    name: str,
    driver: str = "bridge",
    internal: bool = False,
    attachable: bool = False,
    labels: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a Docker network and record ownership."""
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

        # Record ownership
        resource = DockerResource(
            resource_type="network",
            resource_id=network.id,
            user_id=current_user.get("user_id")
        )
        db.add(resource)
        db.commit()

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
@limiter.limit("20/minute")
async def delete_network(
    request: Request,
    network_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a Docker network with ownership check."""
    try:
        network_id = validate_string(network_id, "network_id", max_length=100)
        
        # Check ownership
        check_resource_ownership(db, "network", network_id, current_user)

        docker_service = get_docker_client_service()
        docker_service.connect()
        docker = docker_service.client
        network = docker.networks.get(network_id)
        network.remove()

        # Cleanup ownership record
        db.query(DockerResource).filter(
            DockerResource.resource_type == "network",
            DockerResource.resource_id == network_id
        ).delete()
        db.commit()

        return {"status": "success", "message": f"Network {network_id} deleted"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise DockerAPIError(f"Failed to delete network: {str(e)}")
