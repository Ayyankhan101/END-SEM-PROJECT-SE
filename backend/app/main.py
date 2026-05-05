from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging
import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API metrics storage
api_metrics = {
    "requests": defaultdict(lambda: deque(maxlen=1000)),  # endpoint -> deque of request records
    "total_requests": 0,
    "slow_threshold_seconds": 1.0,  # Log warnings for requests taking > 1 second
}

from app.api import (
    endpoints,
    websocket,
    audit,
    notifications,
    backup,
    docker_resources,
    health,
    ai,
    metrics,
)
from app.db.models import init_db
from app.services.docker_monitor import get_docker_monitor
from app.services.cleanup_service import run_periodic_cleanup
from app.services.scheduler_service import run_scheduler
from app.core.config import load_config
from app.core.security import create_initial_user
from app.core.cors import get_cors_config
from app.core.rate_limiter import limiter
from app.core.exceptions import setup_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DockWatch application...")

    load_config()
    init_db()
    create_initial_user()

    monitor = get_docker_monitor()
    
    # Debug: Show Docker config
    from app.core.config import get_config
    config = get_config()
    logger.info(f"Docker socket path: {config.docker.socket_path}")
    logger.info(f"Docker API version: {config.docker.api_version}")
    
    if monitor.connect():
        logger.info(f"Docker connected: {bool(monitor._container_service)}")
        logger.info(f"Docker client: {monitor._docker_client_service.client}")
        asyncio.create_task(monitor.start_monitoring())
        logger.info("Docker monitoring started")
    else:
        logger.warning("Docker connection failed - running in read-only mode")
        logger.warning("Hint: Check socket path and permissions. Try: sudo chmod 666 /var/run/docker.sock")

    asyncio.create_task(run_periodic_cleanup())
    logger.info("Metrics cleanup job started")

    asyncio.create_task(run_scheduler())
    logger.info("Scheduler service started")

    yield

    logger.info("Shutting down DockWatch...")
    monitor = get_docker_monitor()
    monitor.stop_monitoring()
    monitor.disconnect()


app = FastAPI(
    title="DockWatch API",
    description="Docker Container Health Monitoring System",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add exception handlers
setup_exception_handlers(app)
cors_config = get_cors_config()

app.add_middleware(
    CORSMiddleware,
    **cors_config,
)

# API performance monitoring middleware
@app.middleware("http")
async def measure_response_time(request: Request, call_next):
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    
    # Store metrics
    endpoint = request.url.path
    api_metrics["total_requests"] += 1
    api_metrics["requests"][endpoint].append({
        "timestamp": datetime.now().isoformat(),
        "response_time": process_time,
        "method": request.method,
        "status_code": response.status_code,
    })
    
    # Add response header with process time
    response.headers["X-Process-Time-Seconds"] = f"{process_time:.4f}"
    
    # Log slow requests
    if process_time > api_metrics["slow_threshold_seconds"]:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s (status: {response.status_code})"
        )
    elif process_time > 0.5:  # Info level for moderately slow
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"took {process_time:.2f}s (status: {response.status_code})"
        )
    
    return response

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # CSP - allow same origin and websockets
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ws: wss:"

    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.include_router(endpoints, prefix="/api")
app.include_router(websocket)
app.include_router(audit, prefix="/api")
app.include_router(notifications, prefix="/api")
app.include_router(backup, prefix="/api")
app.include_router(docker_resources, prefix="/api")
app.include_router(health, prefix="/api")
app.include_router(ai, prefix="/api")
app.include_router(metrics, prefix="/api")


@app.get("/")
async def root():
    return {"name": "DockWatch", "version": "1.0.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
