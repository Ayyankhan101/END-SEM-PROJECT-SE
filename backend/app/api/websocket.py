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


async def websocket_callback(data: dict):
    await manager.broadcast(data)


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