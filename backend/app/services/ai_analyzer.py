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
        container_name = anomaly.get('container_name', 'unknown')
        anomaly_type = anomaly.get('anomaly_type', 'unknown')
        severity = anomaly.get('severity', 'medium')
        message = anomaly.get('message', '')
        metric_value = anomaly.get('metric_value', 0)
        threshold = anomaly.get('threshold', 0)
        container_id = anomaly.get('container_id', '')[:12]
        
        cpu = metrics.get('cpu_percent', 0)
        mem = metrics.get('memory_percent', 0)
        
        return f"""You are a senior SRE and DevOps expert specializing in Docker container diagnostics. Analyze this anomaly with deep technical detail.

## Container Context
- Name: {container_name}
- ID: {container_id}
- Image: {anomaly.get('image', 'unknown')}

## Anomaly Details
- Type: {anomaly_type}
- Severity: {severity.upper()}
- Description: {message}
- Measured: {metric_value:.1f}% (threshold: {threshold}%)

## Current Metrics
- CPU Usage: {cpu:.1f}%
- Memory Usage: {mem:.1f}%
- Memory Usage (bytes): {metrics.get('memory_usage', 0) / 1024 / 1024:.1f} MB

## Analysis Required
Provide a detailed JSON response with:
1. "summary": Brief technical summary (1-2 sentences)
2. "root_cause": Detailed root cause analysis - why this is happening
3. "severity": Re-assessed severity (low/medium/high/critical) based on analysis
4. "recommendations": Array of 4-5 specific, actionable remediation steps
5. "confidence": Float 0-1 indicating confidence in analysis
6. "docker_commands": Optional array of docker commands to help diagnose (docker exec, docker logs, etc.)
7. "urgency": "immediate"/"soon"/"monitor" - how quickly action is needed

Format as valid JSON only, no markdown wrapping."""

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
        max_cpu = max(cpu_vals) if cpu_vals else 0
        max_mem = max(mem_vals) if mem_vals else 0
        
        container_name = container.get('name', 'unknown')
        container_id = container.get('id', '')[:12]
        container_status = container.get('status', 'unknown')
        container_image = container.get('image', 'unknown')
        
        trend_cpu = "increasing" if len(cpu_vals) >= 2 and cpu_vals[-1] > cpu_vals[0] else "stable/decreasing"
        trend_mem = "increasing" if len(mem_vals) >= 2 and mem_vals[-1] > mem_vals[0] else "stable/decreasing"
        
        heuristic_context = ""
        if heuristics:
            heuristic_context = f"""
## Heuristic Analysis (automated)
- Summary: {heuristics.get('summary', 'N/A')}
- Possible Cause: {heuristics.get('possible_cause', 'N/A')}
- Severity: {heuristics.get('severity', 'medium')}"""
        
        return f"""You are a senior SRE and Kubernetes/Docker expert. Perform a comprehensive health analysis.

## Container Context
- Name: {container_name}
- ID: {container_id}
- Status: {container_status}
- Image: {container_image}
- CPU Trend: {trend_cpu}
- Memory Trend: {trend_mem}{heuristic_context}

## Metrics Analysis (last {len(metrics)} samples)
| Metric | Current | Avg | Max |
|--------|---------|-----|-----|
| CPU % | {cpu_vals[-1] if cpu_vals else 0:.1f} | {avg_cpu:.1f} | {max_cpu:.1f} |
| Memory % | {mem_vals[-1] if mem_vals else 0:.1f} | {avg_mem:.1f} | {max_mem:.1f} |

## Analysis Required
Provide detailed JSON with:
1. "summary": 2-3 sentence health assessment
2. "root_cause": Primary cause if issues found
3. "severity": low/medium/high/critical
4. "recommendations": 4-5 actionable steps with priority
5. "confidence": 0-1 confidence score
6. "trends": Object with cpu_trend and memory_trend predictions
7. "alert_if": Conditions that should trigger immediate alerts

Return valid JSON only."""

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
        elif provider == "groq":
            return self._generate_groq(prompt)
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

    def _generate_groq(self, prompt: str) -> str:
        """Call Groq API."""
        import requests
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set")
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        payload = {
            "model": os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
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
        """Check if AI provider is accessible."""
        try:
            import requests
            provider = os.getenv("AI_PROVIDER", "ollama").lower()
            
            if provider == "groq":
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    return False
                url = "https://api.groq.com/openai/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
            elif provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    return False
                url = "https://api.openai.com/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
            elif provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    return False
                url = "https://api.anthropic.com/v1/models"
                headers = {"x-api-key": api_key}
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
            elif provider == "together":
                api_key = os.getenv("TOGETHER_API_KEY")
                if not api_key:
                    return False
                url = "https://api.together.xyz/v1/models"
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
            elif self.use_cloud and self.api_key:
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
