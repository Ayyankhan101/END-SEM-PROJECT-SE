"""
Recovery service for automatic container recovery actions.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from app.db.database import get_session
from app.db.models import RecoveryAction
from app.core.config import get_config

logger = logging.getLogger(__name__)


class RecoveryActionType(str, Enum):
    """Types of recovery actions."""
    RESTART = "restart"
    PAUSE = "pause"
    NOTIFY = "notify"
    STOP = "stop"


class RecoveryStatus(str, Enum):
    """Status of recovery actions."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"


class RecoveryService:
    """Service for managing automatic container recovery."""
    
    def __init__(self, container_service, alert_service):
        self.container_service = container_service
        self.alert_service = alert_service
        self.config = get_config()
        self._last_states: Dict[str, str] = {}
        self._recovery_attempts: Dict[str, int] = {}
    
    def check_and_recover(self, container_id: str, container_data: Dict[str, Any]) -> bool:
        """
        Check container state and execute recovery if needed.
        
        Args:
            container_id: The container ID
            container_data: Current container data
            
        Returns:
            True if recovery was triggered, False otherwise
        """
        if not self.config.recovery.enabled:
            return False
        
        current_status = container_data.get("status")
        previous_status = self._last_states.get(container_id)
        
        # Check for unexpected stop
        if previous_status == "running" and current_status != "running":
            logger.warning(f"Container {container_id} stopped unexpectedly")
            
            # Create alert
            self.alert_service.create_alert(
                container_id=container_id,
                alert_type="container_stopped",
                message=f"Container stopped unexpectedly (previous: {previous_status}, current: {current_status})",
                severity="critical"
            )
            
            # Execute recovery actions
            for action in self.config.recovery.actions:
                if self._should_attempt_recovery(container_id, action.type):
                    self.execute_recovery(container_id, action.type)
            
            self._last_states[container_id] = current_status
            return True
        
        self._last_states[container_id] = current_status
        return False
    
    def _should_attempt_recovery(self, container_id: str, action_type: str) -> bool:
        """Check if recovery should be attempted based on max attempts."""
        key = f"{container_id}:{action_type}"
        attempts = self._recovery_attempts.get(key, 0)
        
        # Find max attempts from config
        max_attempts = 3
        for action in self.config.recovery.actions:
            if action.type == action_type:
                max_attempts = action.max_attempts
                break
        
        if attempts >= max_attempts:
            logger.warning(f"Max recovery attempts ({max_attempts}) reached for {key}")
            return False
        
        return True
    
    def execute_recovery(self, container_id: str, action_type: str) -> bool:
        """
        Execute a recovery action on a container.
        
        Args:
            container_id: The container ID
            action_type: Type of recovery action
            
        Returns:
            True if successful, False otherwise
        """
        key = f"{container_id}:{action_type}"
        
        try:
            success = False
            
            if action_type == RecoveryActionType.RESTART:
                success = self.container_service.restart_container(container_id)
            elif action_type == RecoveryActionType.PAUSE:
                success = self.container_service.pause_container(container_id)
            elif action_type == RecoveryActionType.STOP:
                success = self.container_service.stop_container(container_id)
            elif action_type == RecoveryActionType.NOTIFY:
                success = True
            else:
                logger.error(f"Unknown recovery action type: {action_type}")
                return False
            
            # Record the attempt
            self._recovery_attempts[key] = self._recovery_attempts.get(key, 0) + 1
            
            # Log the recovery action
            status_str = "success" if success else "failed"
            self._log_recovery_action(container_id, action_type, status_str)
            
            if success:
                logger.info(f"Recovery action '{action_type}' succeeded for {container_id}")
            else:
                logger.error(f"Recovery action '{action_type}' failed for {container_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Exception during recovery action '{action_type}' for {container_id}: {e}")
            self._log_recovery_action(container_id, action_type, "failed")
            return False
    
    def _log_recovery_action(self, container_id: str, action_type: str, status: str):
        """Log a recovery action to the database."""
        session = get_session()
        try:
            action = RecoveryAction(
                container_id=container_id,
                action_type=action_type,
                status=status
            )
            session.add(action)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log recovery action: {e}")
            session.rollback()
        finally:
            session.close()
    
    def reset_recovery_attempts(self, container_id: str = None):
        """
        Reset recovery attempt counters.
        
        Args:
            container_id: If provided, only reset for this container
        """
        if container_id:
            keys_to_remove = [k for k in self._recovery_attempts.keys() if k.startswith(f"{container_id}:")]
            for key in keys_to_remove:
                del self._recovery_attempts[key]
        else:
            self._recovery_attempts.clear()