"""
Alert management service for DockWatch.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.db.database import get_session
from app.db.models import Alert, Container, AlertRule
from app.core.config import get_config

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing alerts and notifications."""
    
    def __init__(self):
        self.config = get_config()
    
    def get_container_rule(self, container_id: str) -> Optional[AlertRule]:
        """Get alert rule for a specific container."""
        session = get_session()
        try:
            rule = session.query(AlertRule).filter(
                AlertRule.container_id == container_id,
                AlertRule.enabled == 1
            ).first()
            return rule
        finally:
            session.close()
    
    def get_global_rule(self) -> Optional[AlertRule]:
        """Get the global alert rule."""
        session = get_session()
        try:
            rule = session.query(AlertRule).filter(
                AlertRule.container_id == None,
                AlertRule.enabled == 1
            ).first()
            return rule
        finally:
            session.close()
    
    def get_thresholds(self, container_id: str) -> Dict[str, float]:
        """Get effective thresholds for a container (container-specific or global)."""
        rule = self.get_container_rule(container_id)
        if rule:
            return {"cpu": rule.cpu_threshold, "memory": rule.memory_threshold}
        
        global_rule = self.get_global_rule()
        if global_rule:
            return {"cpu": global_rule.cpu_threshold, "memory": global_rule.memory_threshold}
        
        return {"cpu": self.config.monitoring.cpu_threshold, "memory": self.config.monitoring.memory_threshold}
    
    def create_alert(
        self, 
        container_id: str, 
        alert_type: str, 
        message: str, 
        severity: str = "warning"
    ) -> Optional[Alert]:
        """
        Create a new alert.
        
        Args:
            container_id: The container ID
            alert_type: Type of alert (e.g., 'cpu_threshold', 'container_stopped')
            message: Alert message
            severity: Alert severity (info, warning, critical)
            
        Returns:
            Created Alert or None if failed
        """
        session = get_session()
        try:
            alert = Alert(
                container_id=container_id,
                alert_type=alert_type,
                message=message,
                severity=severity,
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            
            logger.info(f"Created alert: {alert_type} for container {container_id}")
            return alert
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def get_alerts(
        self, 
        limit: int = 50, 
        container_id: Optional[str] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None
    ) -> List[Alert]:
        """
        Get alerts with optional filtering.
        
        Args:
            limit: Maximum number of alerts to return
            container_id: Filter by container ID
            severity: Filter by severity
            alert_type: Filter by alert type
            
        Returns:
            List of Alert objects
        """
        session = get_session()
        try:
            query = session.query(Alert).order_by(Alert.timestamp.desc())
            
            if container_id:
                query = query.filter(Alert.container_id == container_id)
            if severity:
                query = query.filter(Alert.severity == severity)
            if alert_type:
                query = query.filter(Alert.alert_type == alert_type)
            
            return query.limit(limit).all()
        finally:
            session.close()
    
    def check_thresholds(self, container_id: str, stats: Dict[str, Any]) -> List[Dict]:
        """
        Check if metrics exceed configured thresholds.
        
        Args:
            container_id: The container ID
            stats: Current container metrics
            
        Returns:
            List of alert dictionaries if thresholds exceeded
        """
        thresholds = self.get_thresholds(container_id)
        cpu_threshold = thresholds["cpu"]
        memory_threshold = thresholds["memory"]
        
        alerts = []
        
        cpu_percent = stats.get("cpu_percent", 0)
        if cpu_percent > cpu_threshold:
            alerts.append({
                "type": "cpu_threshold",
                "message": f"CPU usage {cpu_percent:.1f}% exceeds threshold {cpu_threshold}%",
                "severity": "warning" if cpu_percent < 95 else "critical"
            })
        
        memory_percent = stats.get("memory_percent", 0)
        if memory_percent > memory_threshold:
            alerts.append({
                "type": "memory_threshold",
                "message": f"Memory usage {memory_percent:.1f}% exceeds threshold {memory_threshold}%",
                "severity": "warning" if memory_percent < 95 else "critical"
            })
        
        for alert_data in alerts:
            self.create_alert(
                container_id=container_id,
                alert_type=alert_data["type"],
                message=alert_data["message"],
                severity=alert_data["severity"]
            )
        
        return alerts
    
    def clear_old_alerts(self, days: int = 30) -> int:
        """
        Clear alerts older than specified days.
        
        Args:
            days: Number of days to keep alerts
            
        Returns:
            Number of alerts deleted
        """
        from datetime import timedelta
        
        session = get_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = session.query(Alert).filter(Alert.timestamp < cutoff).delete()
            session.commit()
            logger.info(f"Cleared {result} old alerts")
            return result
        except Exception as e:
            logger.error(f"Failed to clear old alerts: {e}")
            session.rollback()
            return 0
        finally:
            session.close()