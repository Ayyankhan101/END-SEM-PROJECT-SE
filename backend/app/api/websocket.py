from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json
import logging

from app.services.docker_monitor import get_docker_monitor


logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.append(connection)
        
        for ws in disconnected:
            self.disconnect(ws)


manager = ConnectionManager()


def websocket_callback(data: dict):
    """Synchronous wrapper for async broadcast."""
    asyncio.create_task(manager.broadcast(data))


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await manager.connect(websocket)
    monitor = get_docker_monitor()
    monitor.register_callback(websocket_callback)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "status":
                await websocket.send_json({
                    "type": "status",
                    "connections": len(manager.active_connections)
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/health")
async def websocket_health(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.send_json({
                "status": "healthy",
                "connections": len(manager.active_connections)
            })
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/logs/{container_id}")
async def websocket_logs(websocket: WebSocket, container_id: str):
    await websocket.accept()
    logger.info(f"Log stream connected for container: {container_id}")
    
    from app.services.docker_monitor import get_docker_monitor
    monitor = get_docker_monitor()
    
    try:
        async for line in monitor.stream_container_logs(container_id, lines=100):
            await websocket.send_text(line)
    except Exception as e:
        logger.error(f"Log stream error for {container_id}: {e}")
    finally:
        logger.info(f"Log stream disconnected for container: {container_id}")


@router.websocket("/ws/exec/{container_id}")
async def websocket_exec(websocket: WebSocket, container_id: str):
    await websocket.accept()
    logger.info(f"Exec session started for container: {container_id}")
    
    from app.services.docker_monitor import get_docker_monitor
    monitor = get_docker_monitor()
    
    try:
        exec_result = monitor.exec_in_container(container_id, ["/bin/sh"], tty=True, stdin=True)
        if not exec_result:
            await websocket.send_json({"error": "Failed to create exec session"})
            return
        
        exec_id = exec_result.get("exec_id")
        socket = monitor.start_exec(exec_id)
        
        async def forward_stdin():
            try:
                while True:
                    data = await websocket.receive_text()
                    if socket and hasattr(socket, 'send'):
                        socket.send(data.encode())
            except Exception:
                pass
        
        async def forward_stdout():
            try:
                if socket and hasattr(socket, 'recv'):
                    while True:
                        data = await asyncio.to_thread(socket.recv, 4096)
                        if data:
                            await websocket.send_bytes(data)
                        else:
                            break
            except Exception as e:
                logger.error(f"Exec output error: {e}")
        
        await asyncio.gather(forward_stdin(), forward_stdout())
        
    except Exception as e:
        logger.error(f"Exec error for {container_id}: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        logger.info(f"Exec session ended for container: {container_id}")