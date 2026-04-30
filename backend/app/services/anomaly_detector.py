import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    CPU_SPIKE = "cpu_spike"
    CPU_HIGH_SUSTAINED = "cpu_high_sustained"
    MEMORY_LEAK = "memory_leak"
    MEMORY_HIGH = "memory_high"
    DISK_PRESSURE = "disk_pressure"
    NETWORK_ANOMALY = "network_anomaly"
    RESTART_LOOP = "restart_loop"
    STOPPED_UNEXPECTED = "stopped_unexpected"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    container_id: str
    container_name: str
    anomaly_type: AnomalyType
    severity: Severity
    message: str
    metric_value: float
    threshold: float
    timestamp: datetime
    recommendations: List[str]


@dataclass
class AnomalyConfig:
    cpu_spike_threshold: float = 75.0
    cpu_sustained_threshold: float = 65.0
    memory_spike_threshold: float = 80.0
    memory_growth_rate_threshold: float = 5.0
    restart_count_threshold: int = 2
    restart_time_window_minutes: int = 30


class AnomalyDetector:
    def __init__(self, config: Optional[AnomalyConfig] = None):
        self.config = config or AnomalyConfig()
        self._metrics_history: Dict[str, List[Dict]] = {}
        self._restart_history: Dict[str, List[datetime]] = {}

    def analyze_container(self, container: Dict, metrics: List[Dict]) -> List[Anomaly]:
        """Analyze a container for anomalies."""
        anomalies = []
        container_id = container.get("id", "unknown")
        container_name = container.get("name", "unknown")
        
        logger.info(f"Analyzing container {container_name} ({container_id[:8]}...) with {len(metrics)} metrics")
        
        if not metrics:
            if container.get("status") == "exited":
                anomalies.append(Anomaly(
                    container_id=container_id,
                    container_name=container_name,
                    anomaly_type=AnomalyType.STOPPED_UNEXPECTED,
                    severity=Severity.MEDIUM,
                    message=f"Container {container_name} has stopped unexpectedly",
                    metric_value=0,
                    threshold=0,
                    timestamp=datetime.now(),
                    recommendations=[
                        "Check container logs for errors",
                        "Review exit code",
                        "Verify restart policy"
                    ]
                ))
            logger.info(f"Container {container_name}: no metrics available")
            return anomalies
        
        current_metric = metrics[-1] if metrics else {}
        cpu = current_metric.get("cpu_percent", 0) or 0
        memory = current_metric.get("memory_percent", 0) or 0
        
        logger.info(f"Container {container_name}: CPU={cpu}%, Memory={memory}%, threshold={self.config.cpu_spike_threshold}%")
        
        if cpu > self.config.cpu_spike_threshold:
            severity = Severity.HIGH if cpu > 90 else Severity.MEDIUM
            anomalies.append(Anomaly(
                container_id=container_id,
                container_name=container_name,
                anomaly_type=AnomalyType.CPU_SPIKE,
                severity=severity,
                message=f"CPU spike detected: {cpu:.1f}% (threshold: {self.config.cpu_spike_threshold}%)",
                metric_value=cpu,
                threshold=self.config.cpu_spike_threshold,
                timestamp=datetime.now(),
                recommendations=[
                    "Check for runaway processes",
                    "Review recent deployments",
                    "Consider scaling or optimizing"
                ]
            ))

        if memory > self.config.memory_spike_threshold:
            severity = Severity.HIGH if memory > 90 else Severity.MEDIUM
            anomalies.append(Anomaly(
                container_id=container_id,
                container_name=container_name,
                anomaly_type=AnomalyType.MEMORY_HIGH,
                severity=severity,
                message=f"Memory high: {memory:.1f}% (threshold: {self.config.memory_spike_threshold}%)",
                metric_value=memory,
                threshold=self.config.memory_spike_threshold,
                timestamp=datetime.now(),
                recommendations=[
                    "Check for memory leaks",
                    "Review memory limits",
                    "Consider increasing memory allocation"
                ]
            ))

        if len(metrics) >= 10:
            memory_trend = self._analyze_memory_trend(metrics)
            if memory_trend > self.config.memory_growth_rate_threshold:
                anomalies.append(Anomaly(
                    container_id=container_id,
                    container_name=container_name,
                    anomaly_type=AnomalyType.MEMORY_LEAK,
                    severity=Severity.HIGH,
                    message=f"Potential memory leak: {memory_trend:.1f}% growth over {len(metrics)} samples",
                    metric_value=memory_trend,
                    threshold=self.config.memory_growth_rate_threshold,
                    timestamp=datetime.now(),
                    recommendations=[
                        "Analyze heap dumps",
                        "Check for memory leaks in application",
                        "Review object accumulation patterns"
                    ]
                ))

        return anomalies

    def _analyze_memory_trend(self, metrics: List[Dict]) -> float:
        """Calculate memory growth rate over time."""
        if len(metrics) < 2:
            return 0.0
        
        first_memory = metrics[0].get("memory_percent", 0) or 0
        last_memory = metrics[-1].get("memory_percent", 0) or 0
        
        if first_memory == 0:
            return 0.0
        
        growth_rate = ((last_memory - first_memory) / first_memory) * 100
        return growth_rate

    def check_restart_loop(self, container_id: str, restart_count: int) -> Optional[Anomaly]:
        """Check if container is in restart loop."""
        now = datetime.now()
        
        if container_id not in self._restart_history:
            self._restart_history[container_id] = []
        
        self._restart_history[container_id].append(now)
        
        recent_restarts = [
            t for t in self._restart_history[container_id]
            if now - t < timedelta(minutes=self.config.restart_time_window_minutes)
        ]
        
        self._restart_history[container_id] = recent_restarts
        
        if len(recent_restarts) >= self.config.restart_count_threshold:
            return Anomaly(
                container_id=container_id,
                container_name="",
                anomaly_type=AnomalyType.RESTART_LOOP,
                severity=Severity.CRITICAL,
                message=f"Restart loop detected: {len(recent_restarts)} restarts in {self.config.restart_time_window_minutes} minutes",
                metric_value=len(recent_restarts),
                threshold=self.config.restart_count_threshold,
                timestamp=now,
                recommendations=[
                    "Check application logs for crash reasons",
                    "Verify health check configuration",
                    "Review resource limits",
                    "Consider containerizing the application"
                ]
            )
        
        return None

    def analyze_all(self, containers: List[Dict], metrics_map: Dict[str, List[Dict]]) -> List[Anomaly]:
        """Analyze all containers for anomalies."""
        all_anomalies = []
        
        for container in containers:
            container_id = container.get("id", "")
            metrics = metrics_map.get(container_id, [])
            anomalies = self.analyze_container(container, metrics)
            all_anomalies.extend(anomalies)
        
        all_anomalies.sort(key=lambda a: (
            Severity[a.severity.value].value,
            a.timestamp
        ), reverse=True)
        
        return all_anomalies


def get_anomaly_detector() -> AnomalyDetector:
    """Get singleton instance of anomaly detector."""
    if not hasattr(get_anomaly_detector, "_instance"):
        get_anomaly_detector._instance = AnomalyDetector()
    return get_anomaly_detector._instance
