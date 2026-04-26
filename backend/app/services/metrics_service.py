"""
Metrics collection and storage service.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from docker.errors import APIError

from app.db import get_session
from app.db.models import Container, Metric, Alert
from app.core.config import get_config
from app.core.exceptions import ContainerNotFoundException

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for collecting and storing container metrics."""
    
    def __init__(self, docker_client):
        self.docker_client = docker_client
        self.config = get_config()
    
    def get_container_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current stats for a container.
        
        Args:
            container_id: The container ID
            
        Returns:
            Dictionary with stats or None if failed
        """
        if not self.docker_client:
            return None
            
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            return self._calculate_metrics(stats, container_id)
        except APIError as e:
            logger.error(f"Failed to get stats for {container_id}: {e}")
            return None
    
    def _calculate_metrics(self, stats: dict, container_id: str) -> Dict[str, Any]:
        """Calculate CPU and memory metrics from raw Docker stats."""
        # Calculate CPU percentage with defensive checks
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        
        cpu_delta = (
            cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        )
        system_delta = (
            cpu_stats.get("system_cpu_usage", 0)
            - precpu_stats.get("system_cpu_usage", 0)
        )
        cpu_count = cpu_stats.get("online_cpus", 1)
        cpu_percent = (
            (cpu_delta / system_delta * cpu_count * 100) if system_delta > 0 else 0
        )
        
        # Calculate memory percentage with defensive checks
        mem_stats = stats.get("memory_stats", {})
        mem_usage = mem_stats.get("usage", 0)
        mem_limit = mem_stats.get("limit", 1)
        mem_percent = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0
        
        return {
            "container_id": container_id,
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(mem_percent, 2),
            "memory_usage": mem_usage,
            "memory_limit": mem_limit,
        }
    
    def store_metrics_batch(self, metrics_list: List[Dict[str, Any]]) -> bool:
        """Store a batch of metrics in a single transaction."""
        if not metrics_list:
            return True
            
        session = get_session()
        try:
            for stats in metrics_list:
                metric = Metric(
                    container_id=stats.get("container_id"),
                    cpu_percent=stats.get("cpu_percent"),
                    memory_percent=stats.get("memory_percent"),
                    memory_usage=stats.get("memory_usage"),
                )
                session.add(metric)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store metrics batch: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def check_thresholds(self, container_id: str, stats: Dict[str, Any]) -> Optional[Dict]:
        """
        Check if metrics exceed configured thresholds.
        
        Args:
            container_id: The container ID
            stats: The current metrics
            
        Returns:
            Alert data if thresholds exceeded, None otherwise
        """
        config = self.config.monitoring
        alerts = []
        
        if stats.get("cpu_percent", 0) > config.cpu_threshold:
            alerts.append({
                "type": "cpu_threshold",
                "message": f"CPU usage {stats['cpu_percent']:.1f}% exceeds threshold {config.cpu_threshold}%",
                "severity": "warning"
            })
        
        if stats.get("memory_percent", 0) > config.memory_threshold:
            alerts.append({
                "type": "memory_threshold",
                "message": f"Memory usage {stats['memory_percent']:.1f}% exceeds threshold {config.memory_threshold}%",
                "severity": "warning"
            })
        
        return alerts if alerts else None