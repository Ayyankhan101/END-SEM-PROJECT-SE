"""
API Performance Metrics endpoint
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["monitoring"])


@router.get("/performance")
async def get_performance_metrics():
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
async def get_simple_metrics():
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
async def reset_metrics():
    """
    Reset all collected metrics.
    Use with caution - this clears all performance history.
    """
    from app.main import api_metrics
    
    api_metrics["requests"].clear()
    api_metrics["total_requests"] = 0
    
    logger.info("API performance metrics reset")
    return {"status": "success", "message": "Metrics reset successfully"}
