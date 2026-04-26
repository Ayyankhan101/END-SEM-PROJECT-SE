"""
Docker client service for managing Docker connections and basic operations.
"""

import logging
from typing import Optional
import docker
from docker.errors import DockerException, APIError

from app.core.config import get_config
from app.core.exceptions import DockerConnectionException

logger = logging.getLogger(__name__)


class DockerClientService:
    """Service for managing Docker client connections."""

    def __init__(self):
        self.config = get_config().docker
        self._client: Optional[docker.DockerClient] = None

    @property
    def client(self) -> Optional[docker.DockerClient]:
        """Get the Docker client instance."""
        return self._client

    def connect(
        self, socket_path: Optional[str] = None, api_version: Optional[str] = None
    ) -> bool:
        """
        Connect to Docker daemon.

        Args:
            socket_path: Path to Docker socket (defaults to config)
            api_version: Docker API version (defaults to config)

        Returns:
            True if connection successful, False otherwise
        """
        socket = socket_path or self.config.socket_path
        version = api_version or self.config.api_version

        # docker lib 7.x requires unix:// prefix for socket
        if socket.startswith("/") and not socket.startswith("unix://"):
            socket = f"unix:///{socket.lstrip('/')}"
        # Ensure HTTP URLs have proper prefix
        elif socket.startswith("http://") or socket.startswith("https://"):
            pass  # Already has HTTP prefix, use as-is

        try:
            self._client = docker.DockerClient(base_url=socket, version=version)
            self._client.ping()
            logger.info(f"Connected to Docker daemon at {socket}")
            return True
        except DockerException as e:
            logger.error(f"Failed to connect to Docker at {socket}: {e}")
            self._client = None
            return False

    def disconnect(self) -> None:
        """Disconnect from Docker daemon."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Docker client: {e}")
            finally:
                self._client = None
                logger.info("Disconnected from Docker daemon")

    def test_connection(self, socket_path: str, api_version: str = "1.41") -> bool:
        """
        Test connection to a Docker host without changing current connection.

        Args:
            socket_path: Path to Docker socket to test
            api_version: Docker API version

        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_client = docker.DockerClient(base_url=socket_path, version=api_version)
            test_client.ping()
            test_client.close()
            return True
        except DockerException as e:
            logger.error(f"Failed to connect to host {socket_path}: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if currently connected to Docker."""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False


# Singleton instance
_docker_client_service: Optional[DockerClientService] = None


def get_docker_client_service() -> DockerClientService:
    """Get or create the Docker client service singleton."""
    global _docker_client_service
    if _docker_client_service is None:
        _docker_client_service = DockerClientService()
    return _docker_client_service
