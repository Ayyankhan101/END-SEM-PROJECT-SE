import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import docker
from docker.errors import APIError, DockerException

from app.core.config import get_config
from app.db.database import get_session
from app.db.models import Container, Metric, Alert, RecoveryAction


logger = logging.getLogger(__name__)


class DockerMonitor:
    def __init__(self):
        self.config = get_config().docker
        self.client: Optional[docker.DockerClient] = None
        self._running = False
        self._callbacks: List[Callable[[dict], None]] = []
        self._last_states: Dict[str, str] = {}
    
    def connect(self) -> bool:
        try:
            self.client = docker.DockerClient(
                base_url=self.config.socket_path,
                version=self.config.api_version
            )
            self.client.ping()
            logger.info("Connected to Docker daemon")
            return True
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            return False
    
    def disconnect(self):
        if self.client:
            self.client.close()
            self.client = None
    
    def register_callback(self, callback: Callable[[dict], None]):
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, data: dict):
        for callback in self._callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def list_containers(self) -> List[dict]:
        if not self.client:
            return []
        try:
            containers = self.client.containers.list(all=True)
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                    "status": c.status,
                    "created": c.attrs.get("Created"),
                    "state": c.attrs.get("State", {}),
                }
                for c in containers
            ]
        except APIError as e:
            logger.error(f"Failed to list containers: {e}")
            return []
    
    def get_container_stats(self, container_id: str) -> Optional[dict]:
        if not self.client:
            return None
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
            cpu_count = stats["cpu_stats"].get("online_cpus", 1)
            cpu_percent = (cpu_delta / system_delta * cpu_count * 100) if system_delta > 0 else 0
            
            mem_usage = stats["memory_stats"]["usage"]
            mem_limit = stats["memory_stats"]["limit"]
            mem_percent = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0
            
            return {
                "container_id": container_id,
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(mem_percent, 2),
                "memory_usage": mem_usage,
                "memory_limit": mem_limit,
            }
        except APIError as e:
            logger.error(f"Failed to get stats for {container_id}: {e}")
            return None
    
    def get_container_health(self, container_id: str) -> Optional[str]:
        if not self.client:
            return None
        try:
            container = self.client.containers.get(container_id)
            health = container.attrs.get("State", {}).get("Health", {})
            return health.get("Status", "none")
        except APIError:
            return None
    
    def restart_container(self, container_id: str) -> bool:
        if not self.client:
            return False
        try:
            container = self.client.containers.get(container_id)
            container.restart()
            logger.info(f"Restarted container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to restart {container_id}: {e}")
            return False
    
    def pause_container(self, container_id: str) -> bool:
        if not self.client:
            return False
        try:
            container = self.client.containers.get(container_id)
            container.pause()
            logger.info(f"Paused container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to pause {container_id}: {e}")
            return False
    
    def unpause_container(self, container_id: str) -> bool:
        if not self.client:
            return False
        try:
            container = self.client.containers.get(container_id)
            container.unpause()
            logger.info(f"Unpaused container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to unpause {container_id}: {e}")
            return False
    
    def _sync_containers_to_db(self):
        session = get_session()
        try:
            containers = self.list_containers()
            existing_ids = {c.id for c in session.query(Container.id).all()}
            
            for c in containers:
                if c["id"] in existing_ids:
                    db_container = session.query(Container).filter(Container.id == c["id"]).first()
                    if db_container:
                        db_container.name = c["name"]
                        db_container.image = c["image"]
                        db_container.status = c["status"]
                        db_container.last_updated = datetime.utcnow()
                else:
                    db_container = Container(
                        id=c["id"],
                        name=c["name"],
                        image=c["image"],
                        status=c["status"]
                                       )
                    session.add(db_container)
            
            session.commit()
        except Exception as e:
            logger.error(f"Failed to sync containers: {e}")
            session.rollback()
        finally:
            session.close()
    
    def _store_metric(self, container_id: str, stats: dict):
        session = get_session()
        try:
            metric = Metric(
                container_id=container_id,
                cpu_percent=stats.get("cpu_percent"),
                memory_percent=stats.get("memory_percent"),
                memory_usage=stats.get("memory_usage")
            )
            session.add(metric)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to store metric: {e}")
            session.rollback()
        finally:
            session.close()
    
    def _create_alert(self, container_id: str, alert_type: str, message: str, severity: str):
        session = get_session()
        try:
            alert = Alert(
                container_id=container_id,
                alert_type=alert_type,
                message=message,
                severity=severity
            )
            session.add(alert)
            session.commit()
            
            self._notify_callbacks({
                "type": "alert",
                "container_id": container_id,
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            session.rollback()
        finally:
            session.close()
    
    def _execute_recovery(self, container_id: str, action_type: str) -> bool:
        session = get_session()
        try:
            status = "success"
            success = False
            
            if action_type == "restart":
                success = self.restart_container(container_id)
            elif action_type == "pause":
                success = self.pause_container(container_id)
            elif action_type == "notify":
                success = True
            
            status = "success" if success else "failed"
            
            action = RecoveryAction(
                container_id=container_id,
                action_type=action_type,
                status=status
            )
            session.add(action)
            session.commit()
            
            self._notify_callbacks({
                "type": "recovery",
                "container_id": container_id,
                "action_type": action_type,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return success
        except Exception as e:
            logger.error(f"Failed to execute recovery: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def _check_and_recover(self, container_id: str, container_data: dict):
        config = get_config()
        monitoring = config.monitoring
        
        current_status = container_data.get("status")
        previous_status = self._last_states.get(container_id)
        
        if previous_status == "running" and current_status != "running":
            self._create_alert(
                container_id,
                "container_stopped",
                f"Container stopped unexpectedly (previous: {previous_status}, current: {current_status})",
                "critical"
            )
            
            if config.recovery.enabled:
                for action in config.recovery.actions:
                    self._execute_recovery(container_id, action.type)
        
        self._last_states[container_id] = current_status
    
    async def start_monitoring(self):
        self._running = True
        self._sync_containers_to_db()
        
        while self._running:
            try:
                containers = self.list_containers()
                
                for container in containers:
                    container_id = container["id"]
                    
                    stats = self.get_container_stats(container_id)
                    if stats:
                        self._store_metric(container_id, container_id)
                        self._notify_callbacks({
                            "type": "metrics",
                            "container_id": container_id,
                            "stats": stats,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    self._check_and_recover(container_id, container)
                    self._notify_callbacks({
                        "type": "container_update",
                        "container": container,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                await asyncio.sleep(self.config.poll_interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    def stop_monitoring(self):
        self._running = False


_docker_monitor: Optional[DockerMonitor] = None


def get_docker_monitor() -> DockerMonitor:
    global _docker_monitor
    if _docker_monitor is None:
        _docker_monitor = DockerMonitor()
    return _docker_monitor