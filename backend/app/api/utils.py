from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import Container, Stack, DockerResource
from app.core.security import get_user_role

def check_container_ownership(db: Session, container_id: str, current_user: dict) -> Container:
    """
    Verify container exists and current_user has access.
    Admin role bypasses ownership check.
    """
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    # Admin users have full access
    if get_user_role(current_user) == "admin":
        return container

    # Enforce ownership
    token_user_id = current_user.get("user_id")
    if token_user_id is None or container.user_id != token_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this container"
        )
    return container


def check_resource_ownership(db: Session, resource_type: str, resource_id: str, current_user: dict):
    """
    Verify Docker resource (image, volume, network) ownership.
    Admin role bypasses ownership check.
    """
    # Admin users have full access
    if get_user_role(current_user) == "admin":
        return True

    token_user_id = current_user.get("user_id")
    if token_user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user session")

    resource = db.query(DockerResource).filter(
        DockerResource.resource_type == resource_type,
        DockerResource.resource_id == resource_id
    ).first()

    if not resource:
        # If not in DB, assume it's system-managed or pre-existing
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to manage this {resource_type}. Resource ownership not verified."
        )

    if resource.user_id != token_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to access this {resource_type}"
        )
    
    return True


def check_stack_ownership(db: Session, stack_id: int, current_user: dict) -> Stack:
    """
    Verify stack exists and current_user has access.
    """
    stack = db.query(Stack).filter(Stack.id == stack_id).first()
    if not stack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stack not found")

    if get_user_role(current_user) == "admin":
        return stack

    token_user_id = current_user.get("user_id")
    if token_user_id is None or stack.user_id != token_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this stack"
        )
    return stack
