"""
Input validation utilities for DockWatch.
"""
import re
from typing import Optional
from fastapi import HTTPException, status


# Docker container ID validation (64 character hex string or short 12 char form)
CONTAINER_ID_PATTERN = re.compile(r'^[a-f0-9]{12,64}$', re.IGNORECASE)

# Container name validation (alphanumeric, hyphens, underscores, dots)
CONTAINER_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]+$')

# Image name validation
IMAGE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*(/[a-zA-Z0-9][a-zA-Z0-9_.-]*)*(:[a-zA-Z0-9_.-]+)?$')


def validate_container_id(container_id: str) -> str:
    """
    Validate a Docker container ID.
    
    Args:
        container_id: The container ID to validate
        
    Returns:
        The validated container ID
        
    Raises:
        HTTPException: If the container ID is invalid
    """
    if not container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container ID is required"
        )
    
    # Remove any whitespace
    container_id = container_id.strip()
    
    if not CONTAINER_ID_PATTERN.match(container_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid container ID format: {container_id[:12]}..."
        )
    
    return container_id.lower()


def validate_container_name(name: str) -> str:
    """
    Validate a container name.
    
    Args:
        name: The container name to validate
        
    Returns:
        The validated container name
        
    Raises:
        HTTPException: If the container name is invalid
    """
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container name is required"
        )
    
    name = name.strip()
    
    if len(name) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container name must be 64 characters or less"
        )
    
    if not CONTAINER_NAME_PATTERN.match(name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container name must start with alphanumeric and contain only alphanumeric, hyphens, underscores, or dots"
        )
    
    return name


def validate_image_name(image: str) -> str:
    """
    Validate a Docker image name.
    
    Args:
        image: The image name to validate
        
    Returns:
        The validated image name
        
    Raises:
        HTTPException: If the image name is invalid
    """
    if not image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image name is required"
        )
    
    image = image.strip()
    
    if len(image) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image name must be 255 characters or less"
        )
    
    if not IMAGE_NAME_PATTERN.match(image):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image name format"
        )
    
    return image


def validate_positive_int(value: int, field_name: str, max_value: Optional[int] = None) -> int:
    """
    Validate that a value is a positive integer.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        max_value: Optional maximum value
        
    Returns:
        The validated integer
        
    Raises:
        HTTPException: If validation fails
    """
    if not isinstance(value, int) or value < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a positive integer"
        )
    
    if max_value is not None and value > max_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must not exceed {max_value}"
        )
    
    return value