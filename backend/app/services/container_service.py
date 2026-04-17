"""
Container operations service.
"""
import logging
from typing import List, Optional, Dict, Any
from docker.errors import APIError, ImageNotFound

from app.core.exceptions import ContainerNotFoundException, DockerConnectionException

logger = logging.getLogger(__name__)


class ContainerService:
    """Service for Docker container operations."""
    
    def __init__(self, docker_client):
        self.docker_client = docker_client
    
    def list_containers(self, all_containers: bool = True) -> List[Dict[str, Any]]:
        """
        List all Docker containers.
        
        Args:
            all_containers: Whether to include stopped containers
            
        Returns:
            List of container dictionaries
        """
        if not self.docker_client:
            return []
        
        try:
            containers = self.docker_client.containers.list(all=all_containers)
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
    
    def get_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a container.
        
        Args:
            container_id: The container ID
            
        Returns:
            Container details or None if not found
        """
        if not self.docker_client:
            return None
        
        try:
            container = self.docker_client.containers.get(container_id)
            return {
                "id": container.id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "status": container.status,
                "created": container.attrs.get("Created"),
                "state": container.attrs.get("State", {}),
                "config": container.attrs.get("Config", {}),
                "network_settings": container.attrs.get("NetworkSettings", {}),
            }
        except APIError as e:
            logger.error(f"Failed to get container {container_id}: {e}")
            return None
    
    def restart_container(self, container_id: str) -> bool:
        """
        Restart a container.
        
        Args:
            container_id: The container ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.restart()
            logger.info(f"Restarted container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to restart {container_id}: {e}")
            return False
    
    def pause_container(self, container_id: str) -> bool:
        """
        Pause a container.
        
        Args:
            container_id: The container ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.pause()
            logger.info(f"Paused container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to pause {container_id}: {e}")
            return False
    
    def unpause_container(self, container_id: str) -> bool:
        """
        Unpause a container.
        
        Args:
            container_id: The container ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.unpause()
            logger.info(f"Unpaused container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to unpause {container_id}: {e}")
            return False
    
    def stop_container(self, container_id: str) -> bool:
        """
        Stop a container.
        
        Args:
            container_id: The container ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop()
            logger.info(f"Stopped container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to stop {container_id}: {e}")
            return False
    
    def get_container_logs(self, container_id: str, lines: int = 100, tail: bool = True) -> Optional[str]:
        """
        Get logs from a container.
        
        Args:
            container_id: The container ID
            lines: Number of lines to retrieve
            tail: Whether to get the tail of logs
            
        Returns:
            Log string or None if failed
        """
        if not self.docker_client:
            return None
        
        try:
            container = self.docker_client.containers.get(container_id)
            if tail:
                logs = container.logs(
                    tail=lines, stdout=True, stderr=True, timestamps=True
                )
            else:
                logs = container.logs(
                    since=lines, stdout=True, stderr=True, timestamps=True
                )
            return logs.decode("utf-8") if isinstance(logs, bytes) else str(logs)
        except APIError as e:
            logger.error(f"Failed to get logs for {container_id}: {e}")
            return None
    
    def create_container(self, config: dict) -> Optional[dict]:
        """
        Create a new container.
        
        Args:
            config: Container configuration dictionary
            
        Returns:
            Created container info or None if failed
        """
        if not self.docker_client:
            return None
        
        try:
            ports = config.get("ports", {})
            port_bindings = {}
            for container_port, host_port in ports.items():
                port_bindings[f"{container_port}/tcp"] = host_port

            volumes = config.get("volumes", [])
            binds = []
            for vol in volumes:
                if isinstance(vol, dict):
                    binds.append(
                        f"{vol.get('host_path')}:{vol.get('container_path')}:{vol.get('mode', 'rw')}"
                    )

            host_config = {}
            if port_bindings:
                host_config["port_bindings"] = port_bindings
            if binds:
                host_config["binds"] = binds

            if config.get("memory_limit"):
                host_config["mem_limit"] = config.get("memory_limit")
            if config.get("cpu_limit"):
                host_config["cpu_period"] = 100000
                host_config["cpu_quota"] = int(config.get("cpu_limit") * 100000)

            container = self.docker_client.containers.run(
                image=config["image"],
                name=config["name"],
                command=config.get("command"),
                environment=config.get("environment", {}),
                detach=True,
                **host_config,
            )

            logger.info(f"Created container {container.id}")
            return {
                "id": container.id,
                "name": container.name,
                "image": config["image"],
                "status": container.status,
            }
        except (APIError, docker.errors.ImageNotFound) as e:
            logger.error(f"Failed to create container: {e}")
            return None