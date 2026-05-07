"""
Cost and resource waste analysis service.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ResourceSummary:
    total_containers: int
    running_containers: int
    stopped_containers: int
    total_cpu_usage: float
    total_memory_usage: float
    total_memory_limit: float
    memory_waste_percent: float
    potential_savings: float
    idle_containers: List[Dict]
    high_usage_containers: List[Dict]


class CostAnalyzer:
    """Analyze resource waste and potential cost savings."""
    
    def __init__(self):
        self.idle_threshold_cpu = 5.0
        self.idle_threshold_memory = 10.0
        self.oversized_memory_threshold = 80.0
    
    def get_resource_summary(self, containers: List[Dict], metrics_map: Dict[str, List[Dict]]) -> ResourceSummary:
        """Calculate resource usage summary across all containers."""
        
        running = [c for c in containers if c.get("status") == "running"]
        stopped = [c for c in containers if c.get("status") != "running"]
        
        total_cpu = 0.0
        total_mem_usage = 0
        total_mem_limit = 0
        
        idle = []
        high_usage = []
        
        for container in running:
            container_id = container.get("id")
            name = container.get("name", "unknown")
            status = container.get("status", "unknown")
            
            metrics_list = metrics_map.get(container_id, [])
            if metrics_list:
                latest = metrics_list[-1]
                cpu = latest.get("cpu_percent", 0) or 0
                mem_pct = latest.get("memory_percent", 0) or 0
                mem_usage = latest.get("memory_usage", 0) or 0
                
                total_cpu += cpu
                total_mem_usage += mem_usage
                
                if cpu < self.idle_threshold_cpu and mem_pct < self.idle_threshold_memory:
                    idle.append({
                        "container_id": container_id,
                        "name": name,
                        "cpu_percent": round(cpu, 2),
                        "memory_percent": round(mem_pct, 2),
                    })
                
                if cpu > 75 or mem_pct > self.oversized_memory_threshold:
                    high_usage.append({
                        "container_id": container_id,
                        "name": name,
                        "status": status,
                        "cpu_percent": round(cpu, 2),
                        "memory_percent": round(mem_pct, 2),
                    })
            else:
                total_mem_limit += container.get("memory_limit", 0) or 0
        
        total_mem_limit = max(total_mem_limit, 1)
        memory_waste = max(0, 100 - (total_mem_usage / total_mem_limit * 100))
        
        potential_savings = self._calculate_savings(idle, total_mem_usage, total_mem_limit)
        
        return ResourceSummary(
            total_containers=len(containers),
            running_containers=len(running),
            stopped_containers=len(stopped),
            total_cpu_usage=round(total_cpu, 2),
            total_memory_usage=total_mem_usage,
            total_memory_limit=total_mem_limit,
            memory_waste_percent=round(memory_waste, 2),
            potential_savings=round(potential_savings, 2),
            idle_containers=idle,
            high_usage_containers=high_usage,
        )
    
    def _calculate_savings(self, idle_containers: List[Dict], mem_usage: int, mem_limit: int) -> float:
        """Estimate potential savings from stopping idle containers."""
        if not idle_containers or mem_limit == 0:
            return 0
        
        idle_mem = sum(c.get("memory_percent", 0) for c in idle_containers)
        avg_idle_mem_percent = idle_mem / len(idle_containers) if idle_containers else 0
        potential_reduction = (mem_usage / mem_limit * 100) * (avg_idle_mem_percent / 100)
        
        return max(0, mem_usage * 0.00001 * len(idle_containers))
    
    def get_container_efficiency(self, container_id: str, metrics: List[Dict]) -> Dict:
        """Get efficiency score for a single container."""
        if not metrics:
            return {"score": "unknown", "recommendation": "No metrics data"}
        
        cpu_vals = [m.get("cpu_percent", 0) or 0 for m in metrics]
        mem_vals = [m.get("memory_percent", 0) or 0 for m in metrics]
        
        avg_cpu = sum(cpu_vals) / len(cpu_vals) if cpu_vals else 0
        avg_mem = sum(mem_vals) / len(mem_vals) if mem_vals else 0
        
        if avg_cpu < self.idle_threshold_cpu and avg_mem < self.idle_threshold_memory:
            score = "low"
            rec = "Consider stopping container when not in use"
        elif avg_cpu > 75 or avg_mem > 75:
            score = "high"
            rec = "Container may need more resources or optimization"
        else:
            score = "normal"
            rec = "Resource usage is normal"
        
        return {
            "container_id": container_id,
            "avg_cpu_percent": round(avg_cpu, 2),
            "avg_memory_percent": round(avg_mem, 2),
            "score": score,
            "recommendation": rec,
        }


def get_cost_analyzer() -> CostAnalyzer:
    """Get singleton instance."""
    if not hasattr(get_cost_analyzer, "_instance"):
        get_cost_analyzer._instance = CostAnalyzer()
    return get_cost_analyzer._instance