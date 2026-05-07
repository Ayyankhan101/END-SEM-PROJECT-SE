"""
Webhook notification service for Slack, Teams, PagerDuty integration.
"""
import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WebhookPayload:
    title: str
    message: str
    severity: str
    container_id: str
    container_name: str
    timestamp: str


class WebhookNotifier:
    """Send alerts to Slack, Teams, PagerDuty via webhooks."""
    
    def __init__(self):
        self.slack_url: str = ""
        self.teams_url: str = ""
        self.pagerduty_key: str = ""
    
    def load_config(self):
        """Load webhook URLs from config."""
        import os
        from app.core.config import get_config
        
        config = get_config()
        self.slack_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.teams_url = os.getenv("TEAMS_WEBHOOK_URL", "")
        self.pagerduty_key = os.getenv("PAGERDUTY_KEY", "")
    
    def send_alert(self, payload: WebhookPayload) -> Dict[str, bool]:
        """Send alert to all configured webhooks."""
        self.load_config()
        
        results = {
            "slack": self._send_slack(payload) if self.slack_url else "not_configured",
            "teams": self._send_teams(payload) if self.teams_url else "not_configured",
            "pagerduty": self._send_pagerduty(payload) if self.pagerduty_key else "not_configured",
        }
        
        return results
    
    def _send_slack(self, payload: WebhookPayload) -> bool:
        """Send notification to Slack."""
        import requests
        
        if not self.slack_url:
            return False
        
        color = {
            "critical": "#ff0000",
            "high": "#ff6600",
            "medium": "#ffcc00",
            "low": "#00ccff",
            "info": "#cccccc"
        }.get(payload.severity, "#cccccc")
        
        data = {
            "attachments": [{
                "color": color,
                "title": payload.title,
                "text": payload.message,
                "fields": [
                    {"title": "Container", "value": payload.container_name, "short": True},
                    {"title": "Severity", "value": payload.severity.upper(), "short": True},
                    {"title": "Time", "value": payload.timestamp, "short": True}
                ],
                "footer": "DockWatch"
            }]
        }
        
        try:
            response = requests.post(self.slack_url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack webhook failed: {e}")
            return False
    
    def _send_teams(self, payload: WebhookPayload) -> bool:
        """Send notification to Microsoft Teams."""
        import requests
        
        if not self.teams_url:
            return False
        
        severity_color = {
            "critical": "Attention",
            "high": "Warning", 
            "medium": "Caution",
            "low": "Informational",
            "info": "Informational"
        }.get(payload.severity, "Informational")
        
        data = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": {
                "critical": "ff0000",
                "high": "ff6600", 
                "medium": "ffcc00",
                "low": "00ccff"
            }.get(payload.severity, "00ccff"),
            "summary": payload.title,
            "sections": [{
                "activityTitle": payload.title,
                "activitySubtitle": payload.message,
                "facts": [
                    {"name": "Container", "value": payload.container_name},
                    {"name": "Severity", "value": payload.severity.upper()},
                    {"name": "Time", "value": payload.timestamp}
                ]
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View in DockWatch",
                "targets": [{"os": "default", "uri": "/containers"}]
            }]
        }
        
        try:
            response = requests.post(self.teams_url, json=data, timeout=10)
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Teams webhook failed: {e}")
            return False
    
    def _send_pagerduty(self, payload: WebhookPayload) -> bool:
        """Send alert to PagerDuty."""
        import requests
        
        if not self.pagerduty_key:
            return False
        
        severity_map = {
            "critical": "critical",
            "high": "high",
            "medium": "standard",
            "low": "low",
            "info": "low"
        }
        
        data = {
            "routing_key": self.pagerduty_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"{payload.title} - {payload.container_name}",
                "severity": severity_map.get(payload.severity, "low"),
                "source": payload.container_id,
                "timestamp": payload.timestamp,
                "custom_details": {
                    "message": payload.message,
                    "container_id": payload.container_id,
                    "container_name": payload.container_name
                }
            }
        }
        
        try:
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=data,
                timeout=10
            )
            return response.status_code in [200, 202, 201]
        except Exception as e:
            logger.error(f"PagerDuty webhook failed: {e}")
            return False


def get_webhook_notifier() -> WebhookNotifier:
    """Get singleton instance."""
    if not hasattr(get_webhook_notifier, "_instance"):
        get_webhook_notifier._instance = WebhookNotifier()
    return get_webhook_notifier._instance