"""
Docker monitoring orchestrator that coordinates all Docker-related services.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, AsyncIterator

from app.core.config import get_config
from app.services.docker_client import DockerClientService, get_docker_client_service
from app.services.container_service import ContainerService
from app.services.metrics_service import MetricsService
from app.services.alert_service import AlertService
from app.services.recovery_service import RecoveryService

logger = logging.getLogger(__name__)


class DockerMonitor:
    """
    Main orchestrator for Docker monitoring.
    Coordinates between various services for container management,
    metrics collection, alerting, and recovery.
    """
    
    def __init__(self):
        self.config = get_config().docker
        self._running = False
        self._callbacks: List[Callable[[dict], None]] = []
        
        # Initialize services
        self._docker_client_service = get_docker_client_service()
        self._container_service: Optional[ContainerService] = None
        self._metrics_service: Optional[MetricsService] = None
        self._alert_service = AlertService()
        self._recovery_service: Optional[RecoveryService] = None
    
    def connect(self) -> bool:
        """Connect to Docker daemon."""
        if self._docker_client_service.connect():
            # Initialize dependent services after successful connection
            self._container_service = ContainerService(self._docker_client_service.client)
            self._metrics_service = MetricsService(self._docker_client_service.client)
            self._recovery_service = RecoveryService(
                self._container_service, 
                self._alert_service
            )
            return True
        return False
    
    def disconnect(self):
        """Disconnect from Docker daemon."""
        self._docker_client_service.disconnect()
        self._container_service = None
        self._metrics_service = None
        self._recovery_service = None
    
    def test_host_connection(self, socket_path: str, api_version: str = "1.41") -> bool:
        """Test connection to a remote Docker host."""
        return self._docker_client_service.test_connection(socket_path, api_version)
    
    def switch_host(self, socket_path: str, api_version: str = "1.41") -> bool:
        """Switch to a different Docker host."""
        logger.info(f"Switching to host: {socket_path}")
        
        # Disconnect from current host
        self.disconnect()
        
        # Reconfigure and connect to new host
        self._docker_client_service._client = None  # Reset client
        if self._docker_client_service.connect(socket_path, api_version):
            # Initialize dependent services with new client
            self._container_service = ContainerService(self._docker_client_service.client)
            self._metrics_service = MetricsService(self._docker_client_service.client)
            self._recovery_service = RecoveryService(
                self._container_service, 
                self._alert_service
            )
            logger.info(f"Successfully switched to host: {socket_path}")
            return True
        
        logger.error(f"Failed to switch to host: {socket_path}")
        return False
    
    def register_callback(self, callback: Callable[[dict], None]):
        """Register a callback for monitoring events."""
        # Check for duplicates
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[dict], None]):
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, data: dict):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    # Container operations - delegate to ContainerService
    def list_containers(self, all_containers: bool = True) -> List[dict]:
        """List all containers."""
        if self._container_service:
            return self._container_service.list_containers(all_containers)
        return []
    
    def get_container(self, container_id: str) -> Optional[dict]:
        """Get container details."""
        if self._container_service:
            return self._container_service.get_container(container_id)
        return None
    
    def restart_container(self, container_id: str) -> bool:
        """Restart a container."""
        if self._container_service:
            return self._container_service.restart_container(container_id)
        return False
    
    def start_container(self, container_id: str) -> bool:
        """Start a container."""
        if self._container_service:
            return self._container_service.start_container(container_id)
        return False
    
    def pause_container(self, container_id: str) -> bool:
        """Pause a container."""
        if self._container_service:
            return self._container_service.pause_container(container_id)
        return False
    
    def unpause_container(self, container_id: str) -> bool:
        """Unpause a container."""
        if self._container_service:
            return self._container_service.unpause_container(container_id)
        return False
    
    def stop_container(self, container_id: str) -> bool:
        """Stop a container."""
        if self._container_service:
            return self._container_service.stop_container(container_id)
        return False
    
    def get_container_logs(self, container_id: str, lines: int = 100, tail: bool = True) -> Optional[str]:
        """Get container logs."""
        if self._container_service:
            return self._container_service.get_container_logs(container_id, lines, tail)
        return None
    
    async def stream_container_logs(self, container_id: str, lines: int = 100) -> AsyncIterator[str]:
        """Stream container logs in real-time."""
        if self._container_service:
            async for line in self._container_service.stream_logs(container_id, lines):
                yield line
    
    def create_container(self, config: dict) -> Optional[dict]:
        """Create a new container."""
        if self._container_service:
            return self._container_service.create_container(config)
        return None
    
    def remove_container(self, container_id: str) -> bool:
        """Remove a container."""
        if self._container_service:
            return self._container_service.remove_container(container_id)
        return False
    
    def exec_in_container(self, container_id: str, cmd: List[str], tty: bool = True, stdin: bool = False) -> Optional[dict]:
        """Execute a command in a container."""
        if self._container_service:
            return self._container_service.exec_in_container(container_id, cmd, tty, stdin)
        return None
    
    def start_exec(self, exec_id: str):
        """Start an exec instance."""
        if self._container_service:
            return self._container_service.start_exec(exec_id)
        return None

    def update_container_env(self, container_id: str, env_vars: Dict[str, str]) -> bool:
        """Update container environment variables (live update)."""
        if not self.docker_client:
            return False
        try:
            container = self.docker_client.containers.get(container_id)
            current_env = container.attrs.get('Config', {}).get('Env', [])
            env_dict = {}
            for env in current_env:
                if '=' in env:
                    key, val = env.split('=', 1)
                    env_dict[key] = val
            env_dict.update(env_vars)
            new_env = [f"{k}={v}" for k, v in env_dict.items()]
            container.update(env=new_env)
            logger.info(f"Updated env vars for container {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update env vars for {container_id}: {e}")
            return False
    
    def update_container_ports(self, container_id: str, port_bindings: Dict[str, int]) -> bool:
        """Update container port mappings (live update)."""
        if not self.docker_client:
            return False
        try:
            container = self.docker_client.containers.get(container_id)
            current_ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            new_bindings = {}
            for container_port, host_port in port_bindings.items():
                if not container_port.endswith('/tcp'):
                    container_port = f"{container_port}/tcp"
                new_bindings[container_port] = [{'HostPort': str(host_port)}]
            container.update(port_bindings=new_bindings)
            logger.info(f"Updated port bindings for container {container_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update ports for {container_id}: {e}")
            return False
    
    # Metrics operations - delegate to MetricsService
    def get_container_stats(self, container_id: str) -> Optional[dict]:
        """Get container stats."""
        if self._metrics_service:
            return self._metrics_service.get_container_stats(container_id)
        return None
    
    def get_container_metrics(self, container_id: str, limit: int = 100) -> list:
        """Get container metrics history."""
        if self._metrics_service:
            return self._metrics_service.get_metrics(container_id, limit=limit)
        return []
    
    def store_metrics_batch(self, metrics_list: List[dict]) -> bool:
        """Store a batch of metrics."""
        if self._metrics_service:
            return self._metrics_service.store_metrics_batch(metrics_list)
        return False

    def check_thresholds(self, container_id: str, stats: dict):

        """Check metric thresholds."""
        if self._metrics_service:
            return self._metrics_service.check_thresholds(container_id, stats)
        return None
    
    # Recovery operations - delegate to RecoveryService
    def check_and_recover(self, container_id: str, container_data: dict) -> bool:
        """Check container state and recover if needed."""
        if self._recovery_service:
            return self._recovery_service.check_and_recover(container_id, container_data)
        return False
    
    def execute_recovery(self, container_id: str, action_type: str) -> bool:
        """Execute a recovery action."""
        if self._recovery_service:
            return self._recovery_service.execute_recovery(container_id, action_type)
        return False
    
    # Stack operations
    def deploy_stack(self, name: str, compose_file: str) -> bool:
        """Deploy a Docker Compose stack using Python Docker SDK."""
        if not self._docker_client_service.client:
            return False
        try:
            import yaml
            client = self._docker_client_service.client
            compose_data = yaml.safe_load(compose_file)
            if not compose_data or "services" not in compose_data:
                return False

            network_name = f"{name}_default"
            try:
                client.networks.create(network_name, driver="bridge")
            except Exception:
                pass

            for svc_name, svc in compose_data["services"].items():
                image = svc.get("image")
                if not image:
                    continue
                try:
                    client.images.pull(image)
                except Exception:
                    pass
                ports = {}
                for p in svc.get("ports", []):
                    parts = str(p).split(":")
                    if len(parts) == 2:
                        ports[f"{parts[1]}/tcp"] = int(parts[0])
                env = svc.get("environment", [])
                container_name = f"{name}_{svc_name}_1"
                try:
                    old = client.containers.get(container_name)
                    old.remove(force=True)
                except Exception:
                    pass
                client.containers.run(
                    image,
                    name=container_name,
                    detach=True,
                    ports=ports,
                    environment=env,
                    network=network_name,
                    labels={"com.docker.compose.project": name, "com.docker.compose.service": svc_name},
                    restart_policy={"Name": "unless-stopped"},
                )

            logger.info(f"Deployed stack {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to deploy stack: {e}")
            return False
    
    def start_stack(self, name: str, compose_file: str) -> bool:
        """Start a Docker Compose stack using Python Docker SDK."""
        if not self._docker_client_service.client:
            return False
        try:
            client = self._docker_client_service.client
            containers = client.containers.list(all=True, filters={"label": f"com.docker.compose.project={name}"})
            for c in containers:
                c.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start stack: {e}")
            return False
    
    def stop_stack(self, name: str) -> bool:
        """Stop a Docker Compose stack using Python Docker SDK."""
        if not self._docker_client_service.client:
            return False
        try:
            client = self._docker_client_service.client
            containers = client.containers.list(filters={"label": f"com.docker.compose.project={name}"})
            for c in containers:
                c.stop()
            return True
        except Exception as e:
            logger.error(f"Failed to stop stack: {e}")
            return False
    
    # Main monitoring loop
    async def start_monitoring(self):
        """Start the main monitoring loop."""
        self._running = True
        
        # Sync containers to database on startup
        self._sync_containers_to_db()
        
        sync_counter = 0
        while self._running:
            try:
                containers = self.list_containers()
                
                # Sync every iteration to ensure new containers are tracked
                self._sync_containers_to_db()
                
                batch_metrics = []
                for container in containers:
                    container_id = container["id"]
                    
                    # Get stats
                    stats = self.get_container_stats(container_id)
                    if stats:
                        batch_metrics.append(stats)
                        self._notify_callbacks({
                            "type": "metrics",
                            "container_id": container_id,
                            "stats": stats,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        
                        # Check thresholds
                        self.check_thresholds(container_id, stats)
                    
                    # Check for recovery needs
                    self.check_and_recover(container_id, container)
                    
                    # Notify about container update
                    self._notify_callbacks({
                        "type": "container_update",
                        "container": container,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                
                # Store all metrics in one transaction
                if batch_metrics:
                    self.store_metrics_batch(batch_metrics)
                
                await asyncio.sleep(self.config.poll_interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self._running = False
    
    def _sync_containers_to_db(self):
        """Sync Docker containers to database and handle removals."""
        from app.db import get_session
        from app.db.models import Container as DBContainer
        from app.api.websocket import websocket_callback

        session = get_session()
        try:
            containers = self.list_containers()
            current_docker_ids = {c["id"] for c in containers}

            db_containers = session.query(DBContainer).all()
            existing_ids = {c.id for c in db_containers}

            # Get first admin user to assign orphans
            from app.db.models import User
            admin_user = session.query(User).filter(User.role == "admin").first()
            admin_id = admin_user.id if admin_user else None

            logger.info(f"Syncing {len(containers)} containers to DB. Admin ID for orphans: {admin_id}")
            # Update or Add
            for c in containers:
                if c["id"] in existing_ids:
                    db_container = (
                        session.query(DBContainer).filter(DBContainer.id == c["id"]).first()
                    )
                    if db_container:
                        db_container.name = c["name"]
                        db_container.image = c["image"]
                        db_container.status = c["status"]
                        db_container.last_updated = datetime.utcnow()
                        # Assign to admin if no owner
                        if db_container.user_id is None and admin_id:
                            db_container.user_id = admin_id
                else:
                    db_container = DBContainer(
                        id=c["id"],
                        name=c["name"],
                        image=c["image"],
                        status=c["status"],
                        user_id=admin_id  # Default to admin
                    )
                    session.add(db_container)

            # Remove orphans (deleted from Docker directly)
            for db_id in existing_ids:
                if db_id not in current_docker_ids:
                    db_container = session.query(DBContainer).filter(DBContainer.id == db_id).first()
                    if db_container:
                        session.delete(db_container)
                        # Notify frontend about direct deletion
                        websocket_callback({
                            "type": "container_deleted",
                            "container_id": db_id,
                            "timestamp": datetime.utcnow().isoformat()
                        })

            session.commit()
        except Exception as e:
            logger.error(f"Failed to sync containers: {e}")
            session.rollback()
        finally:
            session.close()

# Singleton instance
_docker_monitor: Optional[DockerMonitor] = None


def get_docker_monitor() -> DockerMonitor:
    """Get or create the Docker monitor singleton."""
    global _docker_monitor
    if _docker_monitor is None:
        _docker_monitor = DockerMonitor()
    return _docker_monitor