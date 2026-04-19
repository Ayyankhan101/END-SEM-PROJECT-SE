from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging
import asyncio

from app.api import (
    endpoints,
    websocket,
    audit,
    notifications,
    backup,
    docker_resources,
    health,
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


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DockWatch application...")

    load_config()
    init_db()
    create_initial_user()

    monitor = get_docker_monitor()
    if monitor.connect():
        asyncio.create_task(monitor.start_monitoring())
        logger.info("Docker monitoring started")
    else:
        logger.warning("Docker connection failed - running in read-only mode")

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

cors_config = get_cors_config()

app.add_middleware(
    CORSMiddleware,
    **cors_config,
)

app.include_router(endpoints.router, prefix="/api")
app.include_router(websocket.router)
app.include_router(audit.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(backup.router, prefix="/api")
app.include_router(docker_resources.router, prefix="/api")
app.include_router(health.router, prefix="/api")


@app.get("/")
async def root():
    return {"name": "DockWatch", "version": "1.0.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
