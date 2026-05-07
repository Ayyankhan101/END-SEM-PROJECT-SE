"""
Webhook API endpoints for Slack/Teams/PagerDuty integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import logging
import os

from app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["notifications"])


class WebhookTestRequest(BaseModel):
    webhook_type: str


class WebhookConfig(BaseModel):
    slack_url: Optional[str] = None
    teams_url: Optional[str] = None
    pagerduty_key: Optional[str] = None


def get_current_user_with_auth(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return current_user


@router.post("/test")
async def test_webhook(
    request: WebhookTestRequest,
    current_user: dict = Depends(get_current_user_with_auth)
):
    """Test a webhook by sending a test notification."""
    from app.services.webhook_notifier import get_webhook_notifier, WebhookPayload
    
    notifier = get_webhook_notifier()
    notifier.load_config()
    
    payload = WebhookPayload(
        title="DockWatch Test Alert",
        message="This is a test notification from DockWatch",
        severity="info",
        container_id="test-container",
        container_name="test-container",
        timestamp="2024-01-01T00:00:00"
    )
    
    if request.webhook_type == "slack":
        success = notifier._send_slack(payload)
    elif request.webhook_type == "teams":
        success = notifier._send_teams(payload)
    elif request.webhook_type == "pagerduty":
        success = notifier._send_pagerduty(payload)
    else:
        raise HTTPException(status_code=400, detail="Invalid webhook type")
    
    return {"status": "success" if success else "failed", "webhook": request.webhook_type}


@router.get("/status")
async def get_webhook_status(current_user: dict = Depends(get_current_user_with_auth)):
    """Get webhook configuration status."""
    return {
        "slack_configured": bool(os.getenv("SLACK_WEBHOOK_URL")),
        "teams_configured": bool(os.getenv("TEAMS_WEBHOOK_URL")),
        "pagerduty_configured": bool(os.getenv("PAGERDUTY_KEY")),
    }