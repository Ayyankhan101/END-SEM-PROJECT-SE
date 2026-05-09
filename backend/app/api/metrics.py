"""
API Performance Metrics endpoint
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from app.core.security import get_current_user
from app.api.endpoints import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["monitoring"])


@router.get("/performance")
async def get_performance_metrics(current_user: dict = Depends(get_current_user)):
    """
    Get API performance metrics.
    
    Returns aggregated statistics about endpoint response times,
    total requests, and slow request identification.
    """
    from app.main import api_metrics
    
    # Calculate aggregated statistics
    stats = {}
    total_response_times = []
    
    for endpoint, requests in api_metrics["requests"].items():
        if not requests:
            continue
        
        response_times = [r["response_time"] for r in requests]
        total_response_times.extend(response_times)
        
        stats[endpoint] = {
            "total_requests": len(requests),
            "avg_response_time_seconds": round(sum(response_times) / len(response_times), 4),
            "min_response_time_seconds": round(min(response_times), 4),
            "max_response_time_seconds": round(max(response_times), 4),
            "last_10_avg": round(
                sum(response_times[-10:]) / min(10, len(response_times)), 4
            ) if len(response_times) >= 2 else round(sum(response_times) / len(response_times), 4),
        }
    
    # Identify slowest endpoints
    slowest_endpoints = sorted(
        [(ep, data["avg_response_time_seconds"]) for ep, data in stats.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Get recent slow requests (> 1 second)
    slow_requests = []
    for endpoint, requests in api_metrics["requests"].items():
        for req in requests[-20:]:  # Check last 20 requests per endpoint
            if req["response_time"] > 1.0:
                slow_requests.append({
                    "endpoint": endpoint,
                    "timestamp": req["timestamp"],
                    "response_time": round(req["response_time"], 4),
                    "method": req["method"],
                    "status_code": req["status_code"],
                })
    
    # Sort slow requests by response time (slowest first)
    slow_requests.sort(key=lambda x: x["response_time"], reverse=True)
    
    overall_avg = (
        round(sum(total_response_times) / len(total_response_times), 4)
        if total_response_times else 0.0
    )
    
    return {
        "total_requests": api_metrics["total_requests"],
        "overall_avg_response_time_seconds": overall_avg,
        "endpoint_stats": stats,
        "slowest_endpoints": [
            {"endpoint": ep, "avg_response_time_seconds": rt}
            for ep, rt in slowest_endpoints
        ],
        "recent_slow_requests": slow_requests[:20],  # Top 20 slowest recent requests
        "threshold_seconds": api_metrics["slow_threshold_seconds"],
    }


@router.get("/simple")
async def get_simple_metrics(current_user: dict = Depends(get_current_user)):
    """
    Get simplified metrics for dashboard display.
    Returns total requests and average response time.
    """
    from app.main import api_metrics
    
    total_response_times = []
    for requests in api_metrics["requests"].values():
        total_response_times.extend([r["response_time"] for r in requests])
    
    avg = (
        round(sum(total_response_times) / len(total_response_times), 4)
        if total_response_times else 0.0
    )
    
    return {
        "total_requests": api_metrics["total_requests"],
        "average_response_time_seconds": avg,
    }


@router.post("/reset")
async def reset_metrics(current_user: dict = Depends(require_admin)):
    """
    Reset all collected metrics.
    Use with caution - this clears all performance history.
    """
    from app.main import api_metrics
    
    api_metrics["requests"].clear()
    api_metrics["total_requests"] = 0
    
    logger.info("API performance metrics reset")
    return {"status": "success", "message": "Metrics reset successfully"}


@router.get("/summary")
async def get_resource_summary(current_user: dict = Depends(get_current_user)):
    """
    Get resource usage summary across all containers.
    Returns total containers, running/stopped counts, CPU/memory usage,
    memory waste percentage, and potential savings.
    """
    from app.services.cost_analyzer import get_cost_analyzer
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    if not monitor.connect():
        return {"error": "Failed to connect to Docker"}
    
    containers = monitor.list_containers()
    
    from app.db import get_session
    session = get_session()
    try:
        from app.db.models import Metric
        
        metrics_map = {}
        for container in containers:
            container_id = container.get("id")
            if container_id:
                metrics = (
                    session.query(Metric)
                    .filter(Metric.container_id == container_id)
                    .order_by(Metric.timestamp.desc())
                    .limit(50)
                    .all()
                )
                metrics_map[container_id] = [
                    {
                        "cpu_percent": m.cpu_percent,
                        "memory_percent": m.memory_percent,
                        "memory_usage": m.memory_usage,
                    }
                    for m in metrics
                ]
    finally:
        session.close()
    
    analyzer = get_cost_analyzer()
    summary = analyzer.get_resource_summary(containers, metrics_map)
    
    return {
        "total_containers": summary.total_containers,
        "running_containers": summary.running_containers,
        "stopped_containers": summary.stopped_containers,
        "total_cpu_usage": summary.total_cpu_usage,
        "total_memory_usage": summary.total_memory_usage,
        "total_memory_limit": summary.total_memory_limit,
        "memory_waste_percent": summary.memory_waste_percent,
        "potential_savings": summary.potential_savings,
        "idle_containers": summary.idle_containers,
        "high_usage_containers": summary.high_usage_containers,
    }


@router.get("/export")
async def export_metrics(
    container_id: str = None,
    hours: int = 24,
    format: str = "json",
    current_user: dict = Depends(get_current_user),
):
    """
    Export metrics data.
    
    Args:
        container_id: Filter by container (optional)
        hours: Time range (default 24)
        format: json or csv (default json)
    """
    from app.services.docker_monitor import get_docker_monitor
    from app.db import get_session
    from app.db.models import Metric, Container
    
    monitor = get_docker_monitor()
    if not monitor.connect():
        return {"error": "Failed to connect to Docker"}
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    session = get_session()
    try:
        query = session.query(Metric).filter(Metric.timestamp >= cutoff)
        
        if container_id:
            query = query.filter(Metric.container_id == container_id)
        
        metrics = query.order_by(Metric.timestamp.desc()).all()
        
        data = [
            {
                "container_id": m.container_id,
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "memory_usage": m.memory_usage,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in metrics
        ]
        
        if format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            
            return {
                "format": "csv",
                "data": output.getvalue(),
                "filename": f"metrics_{container_id or 'all'}_{hours}h.csv",
            }
        
        return {
            "format": "json",
            "data": data,
            "count": len(data),
        }
    finally:
        session.close()
