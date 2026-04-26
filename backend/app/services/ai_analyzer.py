import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

logger = logging.getLogger(__name__)


@dataclass
class AIAnalysisResult:
    summary: str
    root_cause: str
    severity: str
    recommendations: List[str]
    confidence: float


class OllamaClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        self.api_key = os.getenv("OLLAMA_API_KEY")
        self.use_cloud = os.getenv("OLLAMA_USE_CLOUD", "false").lower() == "true"

    def analyze_anomaly(self, anomaly: Dict, container_metrics: Dict) -> AIAnalysisResult:
        """Analyze a single anomaly using Ollama."""
        prompt = self._build_prompt(anomaly, container_metrics)
        
        try:
            response = self._generate(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            return AIAnalysisResult(
                summary="AI analysis unavailable",
                root_cause="Connection failed",
                severity=anomaly.get("severity", "medium"),
                recommendations=anomaly.get("recommendations", []),
                confidence=0.0
            )

    def batch_analyze(self, anomalies: List[Dict], metrics_map: Dict[str, Dict]) -> List[AIAnalysisResult]:
        """Analyze multiple anomalies."""
        results = []
        
        for anomaly in anomalies:
            container_id = anomaly.get("container_id", "")
            container_metrics = metrics_map.get(container_id, {})
            result = self.analyze_anomaly(anomaly, container_metrics)
            results.append(result)
        
        return results

    def _build_prompt(self, anomaly: Dict, metrics: Dict) -> str:
        """Build analysis prompt for anomaly."""
        return f"""You are a specialized DevOps AI assistant. Analyze this container anomaly:

Anomaly Details:
- Container: {anomaly.get('container_name', 'unknown')}
- Type: {anomaly.get('anomaly_type', 'unknown')}
- Severity: {anomaly.get('severity', 'medium')}
- Message: {anomaly.get('message', '')}
- Value: {anomaly.get('metric_value', 0)} (threshold: {anomaly.get('threshold', 0)})

Current Metrics:
- CPU: {metrics.get('cpu_percent', 0):.1f}%
- Memory: {metrics.get('memory_percent', 0):.1f}%

Provide:
1. Root cause (Technical)
2. 3 specific recommendations

Format as JSON with keys: summary, root_cause, severity, recommendations[], confidence"""

    def analyze_container_health(self, container: Dict, metrics: List[Dict]) -> AIAnalysisResult:
        """Get overall health analysis for a container with heuristics."""
        
        # Local heuristic analysis first
        heuristics = self._run_heuristics(container, metrics)
        
        # If heuristics found critical issues, we can prioritize them in prompt
        prompt = self._build_health_prompt(container, metrics, heuristics)
        
        try:
            response = self._generate(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Ollama health analysis failed: {e}")
            # Fallback to heuristics only
            return AIAnalysisResult(
                summary=heuristics.get("summary", "Heuristic analysis complete"),
                root_cause=heuristics.get("possible_cause", "Unknown"),
                severity=heuristics.get("severity", "medium"),
                recommendations=heuristics.get("recommendations", []),
                confidence=0.4
            )

    def _run_heuristics(self, container: Dict, metrics: List[Dict]) -> Dict:
        """Simple rule-based analysis."""
        issues = []
        recommendations = []
        severity = "info"
        
        if not metrics:
            return {"summary": "No metrics data", "severity": "low"}
            
        latest = metrics[-1]
        cpu = latest.get("cpu_percent", 0)
        mem = latest.get("memory_percent", 0)
        
        if cpu > 90:
            issues.append("Critical CPU usage")
            recommendations.append("Check for infinite loops or high-load tasks")
            severity = "critical"
        elif cpu > 70:
            issues.append("High CPU usage")
            recommendations.append("Consider scaling up or optimizing workload")
            severity = "high"
            
        if mem > 90:
            issues.append("Memory near limit (Possible OOM risk)")
            recommendations.append("Increase container memory limit")
            severity = "critical"
        elif mem > 75:
            issues.append("High memory usage")
            severity = "high"

        if container.get("status") != "running":
            issues.append(f"Container is {container.get('status')}")
            recommendations.append("Investigate why container stopped/restarted")
            severity = "critical"

        return {
            "summary": " | ".join(issues) if issues else "Container looks healthy",
            "possible_cause": issues[0] if issues else "Normal operation",
            "severity": severity,
            "recommendations": recommendations[:3]
        }

    def _build_health_prompt(self, container: Dict, metrics: List[Dict], heuristics: Dict = None) -> str:
        """Build improved health analysis prompt."""
        cpu_vals = [m.get("cpu_percent", 0) for m in metrics]
        mem_vals = [m.get("memory_percent", 0) for m in metrics]
        
        avg_cpu = sum(cpu_vals) / len(cpu_vals) if cpu_vals else 0
        avg_mem = sum(mem_vals) / len(mem_vals) if mem_vals else 0
        
        heuristic_context = f"\nHeuristic findings: {heuristics.get('summary')}" if heuristics else ""
        
        return f"""You are a specialized Docker & SRE expert. Analyze container health:

Container: {container.get('name', 'unknown')}
Status: {container.get('status', 'unknown')}
Image: {container.get('image', 'unknown')}
{heuristic_context}

Metrics (last {len(metrics)} samples):
- Avg CPU: {avg_cpu:.1f}% | Max CPU: {max(cpu_vals) if cpu_vals else 0:.1f}%
- Avg Memory: {avg_mem:.1f}% | Max Memory: {max(mem_vals) if mem_vals else 0:.1f}%

Provide:
1. Deep health summary (Technical)
2. Likely root cause
3. 3 actionable, specific DevOps recommendations

Format as JSON with keys: summary, root_cause, severity, recommendations[], confidence"""

    def _generate(self, prompt: str) -> str:
        """Call Ollama API (local or cloud)."""
        import requests
        
        if self.use_cloud and self.api_key:
            return self._generate_cloud(prompt)
        else:
            return self._generate_local(prompt)

    def _parse_response(self, response: str) -> AIAnalysisResult:
        """Parse AI response into structured result."""
        import json
        
        try:
            data = json.loads(response)
            return AIAnalysisResult(
                summary=data.get("summary", ""),
                root_cause=data.get("root_cause", ""),
                severity=data.get("severity", "medium"),
                recommendations=data.get("recommendations", []),
                confidence=data.get("confidence", 0.5)
            )
        except json.JSONDecodeError:
            lines = response.strip().split("\n")
            recommendations = [l.strip("- ").strip() for l in lines if l.strip().startswith("-")]
            
            return AIAnalysisResult(
                summary=response[:200],
                root_cause="Parse failed",
                severity="medium",
                recommendations=recommendations[:3],
                confidence=0.3
            )

    def _generate_local(self, prompt: str) -> str:
        """Call local Ollama API."""
        import requests
        
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 512
            }
        }
        
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json().get("response", "")

    def _generate_cloud(self, prompt: str) -> str:
        """Call Ollama Cloud API."""
        import requests
        
        provider = os.getenv("AI_PROVIDER", "ollama").lower()
        
        if provider == "openai":
            return self._generate_openai(prompt)
        elif provider == "anthropic":
            return self._generate_anthropic(prompt)
        elif provider == "together":
            return self._generate_together(prompt)
        else:
            # Default: Ollama cloud
            url = "https://api.ollama.com/v1/chat/completions"
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 512
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def _generate_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        import requests
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        url = "https://api.openai.com/v1/chat/completions"
        
        payload = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 512
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def _generate_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        import requests
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        url = "https://api.anthropic.com/v1/messages"
        
        payload = {
            "model": os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 512
        }
        
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json().get("content", [{}])[0].get("text", "")
    
    def _generate_together(self, prompt: str) -> str:
        """Call Together AI API."""
        import requests
        
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            raise ValueError("TOGETHER_API_KEY not set")
        
        url = "https://api.together.xyz/v1/chat/completions"
        
        payload = {
            "model": os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.1-8B-Instruct-Turbo"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 512
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

    def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            import requests
            if self.use_cloud and self.api_key:
                url = "https://api.ollama.com/v1/models"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
            else:
                url = f"{self.base_url}/api/tags"
                response = requests.get(url, timeout=5)
                return response.status_code == 200
        except Exception:
            return False


def get_ollama_client() -> OllamaClient:
    """Get singleton instance."""
    if not hasattr(get_ollama_client, "_instance"):
        get_ollama_client._instance = OllamaClient()
    return get_ollama_client._instance
