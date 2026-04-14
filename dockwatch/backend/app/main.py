from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

from app.api import endpoints, websocket
from app.db.database import init_db
from app.services.docker_monitor import get_docker_monitor
from app.core.config import load_config
from app.core.security import create_initial_user


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    
    yield
    
    logger.info("Shutting down DockWatch...")
    monitor = get_docker_monitor()
    monitor.stop_monitoring()
    monitor.disconnect()


app = FastAPI(
    title="DockWatch API",
    description="Docker Container Health Monitoring System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix="/api")
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "name": "DockWatch",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)