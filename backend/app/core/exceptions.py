"""
Custom exceptions and exception handlers for DockWatch.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class DockWatchException(Exception):
    """Base exception for DockWatch application."""
    
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ContainerNotFoundException(DockWatchException):
    """Raised when a container is not found."""
    
    def __init__(self, container_id: str):
        super().__init__(
            message=f"Container '{container_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class DockerConnectionException(DockWatchException):
    """Raised when Docker connection fails."""
    
    def __init__(self, message: str = "Failed to connect to Docker daemon"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class ValidationException(DockWatchException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class AuthenticationException(DockWatchException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationException(DockWatchException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


def setup_exception_handlers(app: FastAPI):
    """Configure exception handlers for the FastAPI application."""
    
    @app.exception_handler(DockWatchException)
    async def dockwatch_exception_handler(request: Request, exc: DockWatchException):
        logger.error(f"DockWatchException: {exc.message}", extra={"details": exc.details})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        logger.warning(f"Validation error: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation failed",
                "details": errors
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database error occurred",
                "details": {"message": "Please try again later"}
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "An unexpected error occurred",
                "details": {"message": "Please try again later"}
            }
        )