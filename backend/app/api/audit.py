"""
Audit logging API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
import json

from app.db.models import get_db, AuditLog, User
from app.core.security import get_current_user
from app.core.validation import validate_string, ValidationError

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
async def get_audit_logs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit logs with filtering and pagination"""
    query = db.query(AuditLog)
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    # Filter by date range
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = query.filter(AuditLog.timestamp >= cutoff_date)
    
    # Order by timestamp descending
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    logs = query.offset(skip).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": json.loads(log.details) if log.details else None,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/stats")
async def get_audit_stats(
    request: Request,
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit statistics"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get action counts
    action_counts = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.timestamp >= cutoff_date
    ).group_by(AuditLog.action).all()
    
    # Get resource type counts
    resource_counts = db.query(
        AuditLog.resource_type,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.timestamp >= cutoff_date
    ).group_by(AuditLog.resource_type).all()
    
    # Get daily activity
    daily_activity = db.query(
        func.date(AuditLog.timestamp).label('date'),
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.timestamp >= cutoff_date
    ).group_by(func.date(AuditLog.timestamp)).order_by('date').all()
    
    return {
        "period_days": days,
        "total_actions": sum(count for _, count in action_counts),
        "actions_by_type": {action: count for action, count in action_counts},
        "resources_by_type": {resource: count for resource, count in resource_counts},
        "daily_activity": [{"date": str(date), "count": count} for date, count in daily_activity]
    }


def log_action(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None
):
    """Helper function to log an action"""
    try:
        # Validate inputs
        action = validate_string(action, "action", max_length=50)
        resource_type = validate_string(resource_type, "resource_type", max_length=50)
        if resource_id:
            resource_id = validate_string(resource_id, "resource_id", max_length=100)
        
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address
        )
        db.add(log_entry)
        db.commit()
    except ValidationError as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        # Don't raise - audit logging should not break main functionality
        print(f"Failed to log action: {e}")