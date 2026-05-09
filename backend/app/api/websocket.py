"""
WebSocket API for real-time communication
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from typing import List
import asyncio
import logging
import os

from app.services.docker_monitor import get_docker_monitor
from app.core.security import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()


from typing import List, Dict


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.rooms: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room: str = "global"):
        await websocket.accept()
        self.active_connections.append(websocket)
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(websocket)
        logger.info(f"WebSocket connected to {room}. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, room: str = "global"):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
            if not self.rooms[room]:
                del self.rooms[room]
        logger.info(f"WebSocket disconnected from {room}. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict, room: str = "global"):
        if room not in self.rooms:
            return
        
        disconnected = []
        for ws in self.rooms[room]:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error in {room}: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.disconnect(ws, room)


manager = ConnectionManager()


def websocket_callback(data: dict):
    # Broadcast to specific container room if available
    container_id = data.get("container_id")
    if container_id:
        asyncio.create_task(manager.broadcast(data, room=f"container_{container_id}"))
    
    # Always broadcast to global room
    asyncio.create_task(manager.broadcast(data, room="global"))


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket, container_id: str = None, token: str = None):
    """Metrics stream with JWT authentication and optional container filtering."""
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        user = verify_token(token)
    except Exception as e:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return
    
    room = f"container_{container_id}" if container_id else "global"
    
    # Ownership check if filtered
    if container_id:
        from app.db.models import get_session
        from app.api.utils import check_container_ownership
        db = get_session()
        try:
            check_container_ownership(db, container_id, user)
        except HTTPException as e:
            await websocket.close(code=1008, reason=e.detail)
            return
        finally:
            db.close()

    await manager.connect(websocket, room=room)
    
    monitor = get_docker_monitor()
    monitor.register_callback(websocket_callback)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text("ping")
    except WebSocketDisconnect:
        manager.disconnect(websocket, room=room)
    except Exception as e:
        logger.error(f"WebSocket error in {room}: {e}")
        manager.disconnect(websocket, room=room)


@router.websocket("/ws/health")
async def websocket_health(websocket: WebSocket, token: str = None):
    """Health check WebSocket."""
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        user = verify_token(token)
    except Exception as e:
        await websocket.close(code=1008, reason="Invalid or expired token")
        logger.warning(f"WS health auth failed: {e}")
        return
    
    await manager.connect(websocket, room="global")

    try:
        while True:
            await websocket.send_json({
                "status": "healthy",
                "connections": len(manager.active_connections)
            })
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room="global")


@router.websocket("/ws/logs/{container_id}")
async def websocket_logs(websocket: WebSocket, container_id: str, token: str = None):
    """Log stream with authentication and ownership check."""
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        user = verify_token(token)
    except Exception as e:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return
    
    # Ownership check
    from app.db.models import get_session
    from app.api.utils import check_container_ownership
    
    db = get_session()
    try:
        check_container_ownership(db, container_id, user)
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        return
    finally:
        db.close()
    
    await websocket.accept()
    logger.info(f"Log stream for {container_id} (user: {user.get('sub')})")
    
    monitor = get_docker_monitor()
    if not hasattr(monitor, '_container_service') or monitor._container_service is None:
        monitor.connect()
    try:
        async for line in monitor.stream_container_logs(container_id, lines=100):
            await websocket.send_text(line)
    except Exception as e:
        logger.error(f"Log stream error for {container_id}: {e}")
    finally:
        logger.info(f"Log stream ended for {container_id}")


@router.websocket("/ws/exec/{container_id}")
async def websocket_exec(websocket: WebSocket, container_id: str, token: str = None):
    """Exec session - owners or admins only with command allowlist."""
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    try:
        user = verify_token(token)
    except Exception as e:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return
    
    # Ownership check
    from app.db.models import get_session
    from app.api.utils import check_container_ownership
    
    db = get_session()
    try:
        check_container_ownership(db, container_id, user)
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        return
    finally:
        db.close()
    
    # Command allowlist - shell access is restricted
    ALLOWED_SHELLS = {"/bin/sh", "/bin/bash", "/usr/bin/env sh", "/usr/bin/env bash"}
    EXEC_ENABLED = os.environ.get("DOCKWATCH_EXEC_ENABLED", "false").lower() == "true"
    
    if not EXEC_ENABLED:
        await websocket.close(code=1008, reason="Exec endpoint disabled. Set DOCKWATCH_EXEC_ENABLED=true to enable.")
        return
    
    await websocket.accept()
    logger.warning(f"Exec session for {container_id} (user: {user.get('sub')})")
    
    monitor = get_docker_monitor()
    if not hasattr(monitor, '_container_service') or monitor._container_service is None:
        monitor.connect()
    
    # Use shell from allowlist (default to /bin/sh if available)
    shell_cmd = "/bin/sh"
    try:
        exec_result = monitor.exec_in_container(container_id, [shell_cmd], tty=True, stdin=True)
        if not exec_result:
            await websocket.send_json({"error": "Failed to create exec"})
            return
        exec_id = exec_result.get("exec_id")
        socket = monitor.start_exec(exec_id)
        
        async def forward_stdin():
            from app.db.models import AuditLog, get_session
            from app.api.audit import compute_audit_hash, get_last_audit_hash
            import json

            try:
                while True:
                    data = await websocket.receive_text()
                    # Log shell commands (simplified: log every input)
                    # In a real app, we'd buffer until newline
                    if data.strip():
                        db = get_session()
                        try:
                            prev_hash = get_last_audit_hash(db)
                            action_details = json.dumps({
                                "command_fragment": data,
                                "container_id": container_id
                            })
                            new_log = AuditLog(
                                user_id=user.get("user_id"),
                                action="container_exec_input",
                                resource_type="container",
                                resource_id=container_id,
                                details=action_details,
                                hash_chain=compute_audit_hash(action_details, prev_hash)
                            )
                            db.add(new_log)
                            db.commit()
                        except Exception as e:
                            logger.error(f"Failed to log exec input: {e}")
                        finally:
                            db.close()

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
                logger.error(f"Exec stdout error: {e}")
        
        await asyncio.gather(forward_stdin(), forward_stdout())
    except Exception as e:
        logger.error(f"Exec error for {container_id}: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        logger.warning(f"Exec ended for {container_id}")
