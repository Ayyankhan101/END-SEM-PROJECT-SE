"""
Container operations service.
"""
import logging
import docker
from typing import List, Optional, Dict, Any, AsyncIterator
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
    
    def start_container(self, container_id: str) -> bool:
        """Start a container."""
        if not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.start()
            logger.info(f"Started container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to start {container_id}: {e}")
            return False
    
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
    
    async def stream_logs(self, container_id: str, lines: int = 100) -> AsyncIterator[str]:
        """
        Stream logs from a container in real-time.
        
        Args:
            container_id: The container ID
            lines: Number of lines to buffer
            
        Yields:
            Log lines as they arrive
        """
        if not self.docker_client:
            return
        
        try:
            container = self.docker_client.containers.get(container_id)
            log_generator = container.logs(
                follow=True,
                tail=lines,
                stdout=True,
                stderr=True,
                timestamps=True,
                stream=True
            )
            
            buffer = []
            max_buffer = 10000
            
            for line in log_generator:
                decoded_line = line.decode("utf-8") if isinstance(line, bytes) else str(line)
                buffer.append(decoded_line)
                
                if len(buffer) > max_buffer:
                    buffer = buffer[-max_buffer:]
                
                yield decoded_line
                
        except APIError as e:
            logger.error(f"Failed to stream logs for {container_id}: {e}")
        except Exception as e:
            logger.error(f"Log stream error for {container_id}: {e}")
    
    def remove_container(self, container_id: str) -> bool:
        """
        Remove a container.
        
        Args:
            container_id: The container ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.remove(force=True)
            logger.info(f"Removed container {container_id}")
            return True
        except APIError as e:
            logger.error(f"Failed to remove {container_id}: {e}")
            return False
    
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
        
        image = config.get("image", "")
        
        # Auto-pull image if not exists locally
        try:
            self.docker_client.images.get(image)
            logger.info(f"Image {image} found locally")
        except ImageNotFound:
            logger.info(f"Image {image} not found locally, pulling...")
            try:
                for line in self.docker_client.images.pull(image, stream=True, decode=True):
                    status = line.get('status', '')
                    progress = line.get('progress', '')
                    if status:
                        logger.info(f"Pull {image}: {status} {progress}")
                logger.info(f"Image {image} pulled successfully")
            except Exception as e:
                logger.error(f"Failed to pull image {image}: {e}")
                return {
                    "error": f"Image '{image}' not found and failed to pull. Error: {str(e)}",
                    "suggestion": f"Manually pull image with: docker pull {image}"
                }
        
        try:
            ports = config.get("ports") or {}
            ports_list = []
            for container_port, host_port in ports.items():
                ports_list.append(f"{host_port}:{container_port}")

            volumes = config.get("volumes") or []
            binds = []
            for vol in volumes:
                if isinstance(vol, dict):
                    binds.append(
                        f"{vol.get('host_path')}:{vol.get('container_path')}:{vol.get('mode', 'rw')}"
                    )

            host_config = {}
            if ports_list:
                host_config["ports"] = ports_list
            if binds:
                host_config["binds"] = binds

            if config.get("memory_limit"):
                host_config["mem_limit"] = config.get("memory_limit")
            else:
                host_config["mem_limit"] = "512m"  # Default limit

            if config.get("cpu_limit"):
                host_config["cpu_period"] = 100000
                host_config["cpu_quota"] = int(config.get("cpu_limit") * 100000)
            else:
                host_config["cpu_period"] = 100000
                host_config["cpu_quota"] = 50000  # Default 0.5 CPU

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
        except (APIError, ImageNotFound) as e:
            logger.error(f"Failed to create container '{config.get('name')}': {config.get('image')} - Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating container '{config.get('name')}': {type(e).__name__}: {e}")
            return None
    
    def exec_in_container(self, container_id: str, cmd: List[str], tty: bool = True, stdin: bool = False) -> Optional[dict]:
        """Execute a command in a container."""
        if not self.docker_client:
            return None
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            exec_result = container.exec_create(
                cmd=cmd,
                tty=tty,
                stdin=stdin,
                demux=True
            )
            
            return {
                "exec_id": exec_result.get("Id"),
                "container_id": container_id
            }
        except APIError as e:
            logger.error(f"Failed to exec in {container_id}: {e}")
            return None
    
    def start_exec(self, exec_id: str):
        """Start an exec instance."""
        if not self.docker_client:
            return None
        
        try:
            return self.docker_client.exec_start(
                exec_id=exec_id,
                tty=True,
                detach=False,
                socket=True
            )
        except APIError as e:
            logger.error(f"Failed to start exec {exec_id}: {e}")
            return None

    def pull_image(self, image_name: str, tag: str = "latest") -> bool:
        """Pull an image from Docker Hub."""
        if not self.docker_client:
            return False
        
        try:
            full_image = f"{image_name}:{tag}"
            logger.info(f"Pulling image {full_image}...")
            for line in self.docker_client.images.pull(image_name, tag, stream=True, decode=True):
                status = line.get('status', '')
                progress = line.get('progress', '')
                if status:
                    logger.info(f"Pull {full_image}: {status} {progress}")
            logger.info(f"Successfully pulled {full_image}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull image {image_name}:{tag}: {e}")
            return False