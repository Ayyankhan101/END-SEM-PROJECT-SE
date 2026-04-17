"""
Notification channels and logs API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import httpx
from datetime import datetime

from app.db.models import get_db, NotificationChannel, NotificationLog, Alert, User
from app.core.security import get_current_user
from app.core.validation import validate_string, validate_json, ValidationError

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationChannelCreate:
    name: str
    channel_type: str  # email, webhook, slack, discord
    config: dict
    is_enabled: bool = True


@router.get("/channels")
async def get_notification_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all notification channels"""
    channels = db.query(NotificationChannel).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "channel_type": c.channel_type,
            "config": json.loads(c.config),
            "is_enabled": bool(c.is_enabled),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        }
        for c in channels
    ]


@router.post("/channels")
async def create_notification_channel(
    name: str,
    channel_type: str,
    config: dict,
    is_enabled: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new notification channel"""
    try:
        # Validate inputs
        name = validate_string(name, "name", max_length=100)
        channel_type = validate_string(channel_type, "channel_type", max_length=50)
        
        # Validate channel type
        valid_types = ["email", "webhook", "slack", "discord"]
        if channel_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid channel type. Must be one of: {', '.join(valid_types)}")
        
        # Validate config
        if not isinstance(config, dict):
            raise HTTPException(status_code=400, detail="Config must be a JSON object")
        
        channel = NotificationChannel(
            name=name,
            channel_type=channel_type,
            config=json.dumps(config),
            is_enabled=1 if is_enabled else 0
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        
        return {
            "id": channel.id,
            "name": channel.name,
            "channel_type": channel.channel_type,
            "config": json.loads(channel.config),
            "is_enabled": bool(channel.is_enabled)
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create notification channel: {str(e)}")


@router.delete("/channels/{channel_id}")
async def delete_notification_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a notification channel"""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    db.delete(channel)
    db.commit()
    return {"status": "success", "message": "Notification channel deleted"}


@router.post("/channels/{channel_id}/test")
async def test_notification_channel(
    channel_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test a notification channel"""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    if not channel.is_enabled:
        raise HTTPException(status_code=400, detail="Notification channel is disabled")
    
    # Send test notification in background
    background_tasks.add_task(send_test_notification, channel, db)
    
    return {"status": "success", "message": "Test notification sent"}


async def send_test_notification(channel: NotificationChannel, db: Session):
    """Send a test notification"""
    config = json.loads(channel.config)
    
    test_message = {
        "title": "DockWatch Test Notification",
        "message": "This is a test notification from DockWatch",
        "severity": "info",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        if channel.channel_type == "webhook":
            await send_webhook_notification(config, test_message)
        elif channel.channel_type == "slack":
            await send_slack_notification(config, test_message)
        elif channel.channel_type == "discord":
            await send_discord_notification(config, test_message)
        elif channel.channel_type == "email":
            # Email would be handled by a background worker
            pass
        
        # Log success
        log = NotificationLog(
            channel_id=channel.id,
            status="sent",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        # Log failure
        log = NotificationLog(
            channel_id=channel.id,
            status="failed",
            error_message=str(e),
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()


async def send_webhook_notification(config: dict, message: dict):
    """Send webhook notification"""
    url = config.get("url")
    if not url:
        raise ValueError("Webhook URL not configured")
    
    headers = config.get("headers", {})
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=message, headers=headers, timeout=30.0)
        response.raise_for_status()


async def send_slack_notification(config: dict, message: dict):
    """Send Slack notification"""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("Slack webhook URL not configured")
    
    color = {
        "critical": "#FF0000",
        "warning": "#FFA500",
        "info": "#36A64F"
    }.get(message.get("severity", "info"), "#36A64F")
    
    payload = {
        "attachments": [{
            "color": color,
            "title": message.get("title", "DockWatch Alert"),
            "text": message.get("message", ""),
            "footer": "DockWatch",
            "ts": int(datetime.utcnow().timestamp())
        }]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload, timeout=30.0)
        response.raise_for_status()


async def send_discord_notification(config: dict, message: dict):
    """Send Discord notification"""
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("Discord webhook URL not configured")
    
    color = {
        "critical": 0xFF0000,
        "warning": 0xFFA500,
        "info": 0x36A64F
    }.get(message.get("severity", "info"), 0x36A64F)
    
    payload = {
        "embeds": [{
            "title": message.get("title", "DockWatch Alert"),
            "description": message.get("message", ""),
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DockWatch"
            }
        }]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload, timeout=30.0)
        response.raise_for_status()