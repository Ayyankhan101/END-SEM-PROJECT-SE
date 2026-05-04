import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RemediationAction(Enum):
    NONE = "none"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    RESTART = "restart"
    INCREASE_MEMORY = "increase_memory"
    INCREASE_CPU = "increase_cpu"
    INVESTIGATE_LOGS = "investigate_logs"
    UPDATE_IMAGE = "update_image"
    ADD_HEALTH_CHECK = "add_health_check"
    REVIEW_RESOURCES = "review_resources"


@dataclass
class RemediationPlan:
    action: RemediationAction
    reasoning: str
    estimated_impact: str
    risk_level: str
    steps: List[str]


class RemediationService:
    def __init__(self):
        self.auto_apply = False

    def create_plan(self, anomaly: Dict, analysis: Optional[Dict] = None) -> RemediationPlan:
        """Create remediation plan for an anomaly."""
        anomaly_type = anomaly.get("anomaly_type", "")
        severity = anomaly.get("severity", "medium")
        
        if severity == "critical":
            return self._critical_plan(anomaly_type, anomaly)
        
        if severity == "high":
            return self._high_plan(anomaly_type, anomaly)
        
        return self._medium_plan(anomaly_type, anomaly)

    def _critical_plan(self, anomaly_type: str, anomaly: Dict) -> RemediationPlan:
        """Handle critical severity."""
        if "restart" in anomaly_type.lower():
            return RemediationPlan(
                action=RemediationAction.INVESTIGATE_LOGS,
                reasoning="Critical restart loop detected - need immediate investigation",
                estimated_impact="High",
                risk_level="high",
                steps=[
                    "1. Fetch container logs: docker logs <container_id>",
                    "2. Check exit code: docker inspect <container_id> --format '{{.State.ExitCode}}'",
                    "3. Review health check configuration",
                    "4. Verify resource limits are not exceeded",
                    "5. Consider adding restart policy in docker-compose"
                ]
            )
        
        return RemediationPlan(
            action=RemediationAction.REVIEW_RESOURCES,
            reasoning="Critical anomaly requires immediate attention",
            estimated_impact="High",
            risk_level="high",
            steps=[
                "1. Run: docker stats <container_id>",
                "2. Check application logs",
                "3. Review current resource usage",
                "4. Consider scaling or restarting if safe"
            ]
        )

    def _high_plan(self, anomaly_type: str, anomaly: Dict) -> RemediationPlan:
        """Handle high severity."""
        if "cpu" in anomaly_type.lower():
            return RemediationPlan(
                action=RemediationAction.SCALE_DOWN,
                reasoning="High CPU usage detected",
                estimated_impact="Medium",
                risk_level="medium",
                steps=[
                    "1. Identify process: docker exec <container_id> top",
                    "2. Check for runaway processes",
                    "3. Consider adding CPU limits",
                    "4. Profile application performance",
                    "5. Scale horizontally if needed"
                ]
            )
        
        if "memory" in anomaly_type.lower():
            return RemediationPlan(
                action=RemediationAction.INCREASE_MEMORY,
                reasoning="High memory usage or leak detected",
                estimated_impact="Medium",
                risk_level="medium",
                steps=[
                    "1. Check heap: docker exec <container_id> node --max-old-space-size",
                    "2. Review memory allocation settings",
                    "3. Enable memory profiling if available",
                    "4. Consider increasing memory limits",
                    "5. Investigate potential leaks"
                ]
            )
        
        return RemediationPlan(
            action=RemediationAction.INVESTIGATE_LOGS,
            reasoning="High severity anomaly detected",
            estimated_impact="Medium",
            risk_level="medium",
            steps=[
                "1. Check container logs",
                "2. Review recent changes",
                "3. Analyze metrics history"
            ]
        )

    def _medium_plan(self, anomaly_type: str, anomaly: Dict) -> RemediationPlan:
        """Handle medium severity."""
        if "cpu" in anomaly_type.lower():
            return RemediationPlan(
                action=RemediationAction.REVIEW_RESOURCES,
                reasoning="Elevated CPU usage",
                estimated_impact="Low",
                risk_level="low",
                steps=[
                    "1. Monitor for 5-10 minutes",
                    "2. Check if related to incoming traffic",
                    "3. Review application logs",
                    "4. Consider optimization if sustained"
                ]
            )
        
        if "memory" in anomaly_type.lower():
            return RemediationPlan(
                action=RemediationAction.REVIEW_RESOURCES,
                reasoning="Elevated memory usage",
                estimated_impact="Low",
                risk_level="low",
                steps=[
                    "1. Monitor for growth pattern",
                    "2. Check for memory leaks",
                    "3. Review application memory management"
                ]
            )
        
        return RemediationPlan(
            action=RemediationAction.NONE,
            reasoning="No immediate action required",
            estimated_impact="None",
            risk_level="none",
            steps=[
                "Monitor and reassess if severity increases"
            ]
        )

    def batch_create_plans(self, anomalies: List[Dict]) -> List[RemediationPlan]:
        """Create plans for multiple anomalies."""
        plans = []
        
        for anomaly in anomalies:
            plan = self.create_plan(anomaly)
            plans.append(plan)
        
        return plans


def get_remediation_service() -> RemediationService:
    """Get singleton instance."""
    if not hasattr(get_remediation_service, "_instance"):
        get_remediation_service._instance = RemediationService()
    return get_remediation_service._instance