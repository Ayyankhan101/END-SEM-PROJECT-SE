from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.core.security import get_current_user
from app.services.anomaly_detector import get_anomaly_detector, AnomalyDetector
from app.services.ai_analyzer import get_ollama_client, OllamaClient
from app.services.remediation import get_remediation_service, RemediationService

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/health")
async def ai_health_check():
    """Check AI services availability."""
    import os
    ollama = get_ollama_client()
    ollama_available = ollama.health_check()
    
    provider = os.getenv("AI_PROVIDER", "ollama").lower()
    
    return {
        provider: {
            "available": ollama_available,
            "model": ollama.model,
            "endpoint": ollama.base_url
        }
    }


@router.get("/anomalies")
async def get_anomalies():
    """Get detected anomalies."""
    from app.services.docker_monitor import get_docker_monitor
    
    try:
        monitor = get_docker_monitor()
        containers = monitor.list_containers()
        
        metrics_map = {}
        for container in containers:
            container_id = container.get("id", "")
            try:
                metrics = monitor.get_container_metrics(container_id, limit=20)
                metrics_map[container_id] = metrics
            except Exception as e:
                logger.warning(f"Failed to get metrics for container {container_id}: {e}")
                metrics_map[container_id] = []
        
        detector = get_anomaly_detector()
        anomalies = detector.analyze_all(containers, metrics_map)
        
        return {
            "anomalies": [
                {
                    "id": f"{a.container_id[:8]}_{a.anomaly_type.value}",
                    "container_id": a.container_id,
                    "container_name": a.container_name,
                    "anomaly_type": a.anomaly_type.value,
                    "severity": a.severity.value,
                    "message": a.message,
                    "metric_value": a.metric_value,
                    "threshold": a.threshold,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "recommendations": a.recommendations
                }
                for a in anomalies
            ],
            "count": len(anomalies)
        }
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect anomalies: {str(e)}"
        )


@router.post("/analyze/{container_id}")
async def analyze_container(
    container_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Analyze a specific container."""
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    container = monitor.get_container(container_id)
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    metrics = monitor.get_container_metrics(container_id, limit=20)
    
    detector = get_anomaly_detector()
    anomalies = detector.analyze_container(container, metrics)
    
    ollama = get_ollama_client()
    ai_results = []
    
    for anomaly in anomalies:
        anomaly_dict = {
            "container_id": anomaly.container_id,
            "container_name": anomaly.container_name,
            "anomaly_type": anomaly.anomaly_type.value,
            "severity": anomaly.severity.value,
            "message": anomaly.message,
            "metric_value": anomaly.metric_value,
            "threshold": anomaly.threshold,
            "timestamp": anomaly.timestamp.isoformat(),
            "recommendations": anomaly.recommendations
        }
        
        result = ollama.analyze_anomaly(anomaly_dict, metrics[-1] if metrics else {})
        ai_results.append({
            "anomaly": anomaly_dict,
            "analysis": {
                "summary": result.summary,
                "root_cause": result.root_cause,
                "severity": result.severity,
                "recommendations": result.recommendations,
                "confidence": result.confidence
            }
        })
    
    if not ai_results:
        health_result = ollama.analyze_container_health(container, metrics)
        return {
            "container": container,
            "metrics_summary": {
                "sample_count": len(metrics),
                "avg_cpu": sum(m.get("cpu_percent", 0) for m in metrics) / max(len(metrics), 1),
                "avg_memory": sum(m.get("memory_percent", 0) for m in metrics) / max(len(metrics), 1)
            },
            "analysis": {
                "summary": health_result.summary,
                "root_cause": health_result.root_cause,
                "severity": health_result.severity,
                "recommendations": health_result.recommendations,
                "confidence": health_result.confidence
            }
        }
    
    return {"analyses": ai_results}


@router.get("/remediation/{container_id}")
async def get_remediation(container_id: str):
    """Get remediation plan for a container."""
    from app.services.docker_monitor import get_docker_monitor
    
    monitor = get_docker_monitor()
    container = monitor.get_container(container_id)
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    metrics = monitor.get_container_metrics(container_id, limit=20)
    metrics_dict = metrics[-1] if metrics else {}
    
    detector = get_anomaly_detector()
    anomalies = detector.analyze_container(container, metrics)
    
    remediation = get_remediation_service()
    plans = []
    
    for anomaly in anomalies:
        anomaly_dict = {
            "container_id": anomaly.container_id,
            "container_name": anomaly.container_name,
            "anomaly_type": anomaly.anomaly_type.value,
            "severity": anomaly.severity.value,
            "message": anomaly.message,
            "metric_value": anomaly.metric_value,
            "threshold": anomaly.threshold
        }
        
        plan = remediation.create_plan(anomaly_dict)
        plans.append({
            "anomaly": anomaly_dict,
            "plan": {
                "action": plan.action.value,
                "reasoning": plan.reasoning,
                "estimated_impact": plan.estimated_impact,
                "risk_level": plan.risk_level,
                "steps": plan.steps
            }
        })
    
    if not anomalies:
        return {
            "status": "healthy",
            "message": "No anomalies detected",
            "plans": []
        }
    
    return {"plans": plans}


@router.get("/insights")
async def get_ai_insights():
    """Get overall AI insights dashboard."""
    from app.services.docker_monitor import get_docker_monitor
    
    try:
        monitor = get_docker_monitor()
        containers = monitor.list_containers()
    except Exception as e:
        logger.error(f"AI Insights - failed to list containers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list containers: {str(e)}")
    
    try:
        detector = get_anomaly_detector()
        ollama = get_ollama_client()
        remediation = get_remediation_service()
    except Exception as e:
        logger.error(f"AI Insights - failed to initialize services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initialize services: {str(e)}")
    
    metrics_map = {}
    for container in containers:
        container_id = container.get("id", "")
        try:
            metrics_map[container_id] = monitor.get_container_metrics(container_id, limit=20)
        except Exception as e:
            logger.warning(f"Failed to get metrics for container {container_id}: {e}")
            metrics_map[container_id] = []
    
    all_anomalies = []
    for container in containers:
        container_id = container.get("id", "")
        metrics = metrics_map.get(container_id, [])
        try:
            anomalies = detector.analyze_container(container, metrics)
        except Exception as e:
            logger.error(f"Failed to analyze container {container_id}: {e}", exc_info=True)
            continue
        
        for anomaly in anomalies:
            try:
                anomaly_dict = {
                    "container_id": anomaly.container_id,
                    "container_name": anomaly.container_name,
                    "anomaly_type": anomaly.anomaly_type.value,
                    "severity": anomaly.severity.value,
                    "message": anomaly.message,
                    "metric_value": anomaly.metric_value,
                    "threshold": anomaly.threshold,
                    "timestamp": anomaly.timestamp.isoformat() if anomaly.timestamp else None,
                    "recommendations": anomaly.recommendations
                }
                
                plan = remediation.create_plan(anomaly_dict)
                
                all_anomalies.append({
                    "anomaly": anomaly_dict,
                    "remediation": {
                        "action": plan.action.value,
                        "reasoning": plan.reasoning,
                        "steps": plan.steps
                    }
                })
            except Exception as e:
                logger.error(f"Failed to process anomaly: {e}", exc_info=True)
                continue
    
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for a in all_anomalies:
        s = a.get("anomaly", {}).get("severity", "low")
        if s in severity_counts:
            severity_counts[s] += 1
    
    return {
        "summary": {
            "total_containers": len(containers),
            "anomaly_count": len(all_anomalies),
            "severity_breakdown": severity_counts
        },
        "anomalies": all_anomalies,
        "provider_available": ollama.health_check()
    }