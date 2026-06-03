import os
import re
import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"low", "medium", "high", "critical", "info"}

# OpenAI-compatible providers share the same chat-completions schema. Each entry:
# (env var holding the key, chat endpoint, default model).
OPENAI_COMPATIBLE = {
    "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    "together": ("TOGETHER_API_KEY", "https://api.together.xyz/v1/chat/completions", "meta-llama/Llama-3.1-8B-Instruct-Turbo"),
    "ollama-cloud": ("OLLAMA_API_KEY", "https://api.ollama.com/v1/chat/completions", "llama3"),
}

# /models-style health endpoints for the same providers.
HEALTH_ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "together": "https://api.together.xyz/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
    "ollama-cloud": "https://api.ollama.com/v1/models",
}

SYSTEM_PROMPT = (
    "You are a senior SRE and Docker/Kubernetes diagnostics expert. "
    "You respond with a single valid JSON object and nothing else — no prose, "
    "no markdown fences. All requested keys must be present."
)


@dataclass
class AIAnalysisResult:
    summary: str
    root_cause: str
    severity: str
    recommendations: List[str]
    confidence: float


class OllamaClient:
    """LLM analysis client. Despite the name it routes to whichever provider
    AI_PROVIDER selects (groq/openai/anthropic/together/ollama[-cloud])."""

    def __init__(self, base_url: Optional[str] = None):
        self.provider = os.getenv("AI_PROVIDER", "ollama").lower()
        self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        self.max_retries = int(os.getenv("AI_MAX_RETRIES", "2"))
        self.max_tokens = int(os.getenv("AI_MAX_TOKENS", "1024"))
        self.api_key = os.getenv("OLLAMA_API_KEY")
        self.use_cloud = os.getenv("OLLAMA_USE_CLOUD", "false").lower() == "true"
        self.model = self._resolve_model()

    # ------------------------------------------------------------------ #
    # Configuration helpers
    # ------------------------------------------------------------------ #
    def _resolve_model(self) -> str:
        """Effective model name for the active provider (for display + calls)."""
        if self.provider == "groq":
            return os.getenv("GROQ_MODEL", OPENAI_COMPATIBLE["groq"][2])
        if self.provider == "openai":
            return os.getenv("OPENAI_MODEL", OPENAI_COMPATIBLE["openai"][2])
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        if self.provider == "together":
            return os.getenv("TOGETHER_MODEL", OPENAI_COMPATIBLE["together"][2])
        if self.use_cloud:
            return os.getenv("OLLAMA_MODEL", "llama3")
        return os.getenv("OLLAMA_MODEL", "llama3")

    @property
    def endpoint(self) -> str:
        """Human-readable endpoint for the active provider (health display)."""
        if self.provider in HEALTH_ENDPOINTS and self.provider != "ollama-cloud":
            return HEALTH_ENDPOINTS[self.provider]
        if self.use_cloud:
            return HEALTH_ENDPOINTS["ollama-cloud"]
        return self.base_url

    # ------------------------------------------------------------------ #
    # Public analysis API
    # ------------------------------------------------------------------ #
    def analyze_anomaly(self, anomaly: Dict, container_metrics: Dict) -> AIAnalysisResult:
        """Analyze a single anomaly with the LLM, falling back to the anomaly's
        own recommendations if the provider is unreachable."""
        prompt = self._build_prompt(anomaly, container_metrics)
        try:
            response = self._generate(prompt)
            return self._parse_response(response, fallback_severity=anomaly.get("severity", "medium"))
        except Exception as e:
            logger.error(f"AI anomaly analysis failed ({self.provider}/{self.model}): {e}")
            return AIAnalysisResult(
                summary="AI analysis unavailable — showing rule-based recommendations.",
                root_cause=f"LLM provider '{self.provider}' unreachable: {e}",
                severity=anomaly.get("severity", "medium"),
                recommendations=anomaly.get("recommendations", []),
                confidence=0.0,
            )

    def batch_analyze(self, anomalies: List[Dict], metrics_map: Dict[str, Dict]) -> List[AIAnalysisResult]:
        results = []
        for anomaly in anomalies:
            container_id = anomaly.get("container_id", "")
            container_metrics = metrics_map.get(container_id, {})
            results.append(self.analyze_anomaly(anomaly, container_metrics))
        return results

    def analyze_container_health(self, container: Dict, metrics: List[Dict]) -> AIAnalysisResult:
        """Overall health analysis, blending local heuristics with the LLM."""
        heuristics = self._run_heuristics(container, metrics)
        prompt = self._build_health_prompt(container, metrics, heuristics)
        try:
            response = self._generate(prompt)
            return self._parse_response(response, fallback_severity=heuristics.get("severity", "medium"))
        except Exception as e:
            logger.error(f"AI health analysis failed ({self.provider}/{self.model}): {e}")
            return AIAnalysisResult(
                summary=heuristics.get("summary", "Heuristic analysis complete"),
                root_cause=heuristics.get("possible_cause", "Unknown"),
                severity=heuristics.get("severity", "medium"),
                recommendations=heuristics.get("recommendations", []),
                confidence=0.4,
            )

    # ------------------------------------------------------------------ #
    # Heuristics (local, no LLM)
    # ------------------------------------------------------------------ #
    def _run_heuristics(self, container: Dict, metrics: List[Dict]) -> Dict:
        issues, recommendations = [], []
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
            issues.append("Memory near limit (possible OOM risk)")
            recommendations.append("Increase container memory limit")
            severity = "critical"
        elif mem > 75:
            issues.append("High memory usage")
            severity = "high" if severity != "critical" else severity

        if container.get("status") != "running":
            issues.append(f"Container is {container.get('status')}")
            recommendations.append("Investigate why container stopped/restarted")
            severity = "critical"

        return {
            "summary": " | ".join(issues) if issues else "Container looks healthy",
            "possible_cause": issues[0] if issues else "Normal operation",
            "severity": severity,
            "recommendations": recommendations[:3],
        }

    # ------------------------------------------------------------------ #
    # Prompt builders
    # ------------------------------------------------------------------ #
    def _build_prompt(self, anomaly: Dict, metrics: Dict) -> str:
        metric_value = anomaly.get("metric_value", 0) or 0
        threshold = anomaly.get("threshold", 0) or 0
        cpu = metrics.get("cpu_percent", 0) or 0
        mem = metrics.get("memory_percent", 0) or 0
        mem_mb = (metrics.get("memory_usage", 0) or 0) / 1024 / 1024

        return f"""Analyze this Docker container anomaly with deep technical detail.

## Container Context
- Name: {anomaly.get('container_name', 'unknown')}
- ID: {anomaly.get('container_id', '')[:12]}
- Image: {anomaly.get('image', 'unknown')}

## Anomaly Details
- Type: {anomaly.get('anomaly_type', 'unknown')}
- Severity: {str(anomaly.get('severity', 'medium')).upper()}
- Description: {anomaly.get('message', '')}
- Measured: {metric_value:.1f}% (threshold: {threshold}%)

## Current Metrics
- CPU Usage: {cpu:.1f}%
- Memory Usage: {mem:.1f}%
- Memory Usage (bytes): {mem_mb:.1f} MB

Return a JSON object with keys:
- "summary": 1-2 sentence technical summary
- "root_cause": detailed root-cause analysis
- "severity": one of low/medium/high/critical
- "recommendations": array of 4-5 specific, actionable steps
- "confidence": float 0-1
- "docker_commands": array of helpful diagnostic docker commands
- "urgency": one of immediate/soon/monitor"""

    def _build_health_prompt(self, container: Dict, metrics: List[Dict], heuristics: Dict = None) -> str:
        cpu_vals = [m.get("cpu_percent", 0) for m in metrics]
        mem_vals = [m.get("memory_percent", 0) for m in metrics]
        avg_cpu = sum(cpu_vals) / len(cpu_vals) if cpu_vals else 0
        avg_mem = sum(mem_vals) / len(mem_vals) if mem_vals else 0
        max_cpu = max(cpu_vals) if cpu_vals else 0
        max_mem = max(mem_vals) if mem_vals else 0
        trend_cpu = "increasing" if len(cpu_vals) >= 2 and cpu_vals[-1] > cpu_vals[0] else "stable/decreasing"
        trend_mem = "increasing" if len(mem_vals) >= 2 and mem_vals[-1] > mem_vals[0] else "stable/decreasing"

        heuristic_context = ""
        if heuristics:
            heuristic_context = f"""
## Heuristic Analysis (automated)
- Summary: {heuristics.get('summary', 'N/A')}
- Possible Cause: {heuristics.get('possible_cause', 'N/A')}
- Severity: {heuristics.get('severity', 'medium')}"""

        return f"""Perform a comprehensive health analysis of this Docker container.

## Container Context
- Name: {container.get('name', 'unknown')}
- ID: {container.get('id', '')[:12]}
- Status: {container.get('status', 'unknown')}
- Image: {container.get('image', 'unknown')}
- CPU Trend: {trend_cpu}
- Memory Trend: {trend_mem}{heuristic_context}

## Metrics (last {len(metrics)} samples)
| Metric | Current | Avg | Max |
|--------|---------|-----|-----|
| CPU % | {cpu_vals[-1] if cpu_vals else 0:.1f} | {avg_cpu:.1f} | {max_cpu:.1f} |
| Memory % | {mem_vals[-1] if mem_vals else 0:.1f} | {avg_mem:.1f} | {max_mem:.1f} |

Return a JSON object with keys:
- "summary": 2-3 sentence health assessment
- "root_cause": primary cause if issues found, else "none"
- "severity": one of low/medium/high/critical
- "recommendations": array of 4-5 actionable steps
- "confidence": float 0-1"""

    # ------------------------------------------------------------------ #
    # Generation — routes by provider, with retries
    # ------------------------------------------------------------------ #
    def _generate(self, prompt: str) -> str:
        """Dispatch to the configured provider. Routes by AI_PROVIDER first;
        only falls back to local Ollama when no cloud provider is selected."""
        if self.provider in OPENAI_COMPATIBLE:
            return self._generate_openai_compatible(self.provider, prompt)
        if self.provider == "anthropic":
            return self._generate_anthropic(prompt)
        if self.use_cloud:
            # Generic Ollama-cloud (OpenAI-compatible schema).
            return self._generate_openai_compatible("ollama-cloud", prompt)
        return self._generate_local(prompt)

    def _request_with_retries(self, method: str, url: str, **kwargs) -> requests.Response:
        """HTTP with retry/backoff on transient failures (timeouts, 5xx, 429)."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.request(method, url, timeout=self.timeout, **kwargs)
                if resp.status_code == 429 or resp.status_code >= 500:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after and retry_after.replace(".", "").isdigit() else (2 ** attempt)
                    if attempt < self.max_retries:
                        logger.warning(f"AI provider {resp.status_code} on attempt {attempt + 1}; retrying in {wait:.1f}s")
                        time.sleep(min(wait, 10))
                        continue
                resp.raise_for_status()
                return resp
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exc = e
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.warning(f"AI provider connection error on attempt {attempt + 1}: {e}; retrying in {wait}s")
                    time.sleep(wait)
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("AI request failed without a specific error")

    def _generate_openai_compatible(self, provider: str, prompt: str) -> str:
        env_key, url, default_model = OPENAI_COMPATIBLE[provider]
        api_key = os.getenv(env_key)
        if not api_key:
            raise ValueError(f"{env_key} not set")

        model = self.model if provider == self.provider else default_model
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        started = time.time()
        try:
            resp = self._request_with_retries("POST", url, json=payload, headers=headers)
        except requests.exceptions.HTTPError as e:
            # Some providers reject response_format / json mode — retry once without it.
            if e.response is not None and e.response.status_code == 400 and "response_format" in payload:
                logger.warning(f"{provider} rejected json mode; retrying without response_format")
                payload.pop("response_format", None)
                resp = self._request_with_retries("POST", url, json=payload, headers=headers)
            else:
                raise
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info(f"AI generate ok: {provider}/{model} in {time.time() - started:.2f}s, {len(content)} chars")
        return content

    def _generate_anthropic(self, prompt: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": self.max_tokens,
        }
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        resp = self._request_with_retries("POST", url, json=payload, headers=headers)
        return resp.json().get("content", [{}])[0].get("text", "")

    def _generate_local(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.3, "num_predict": self.max_tokens},
        }
        resp = self._request_with_retries("POST", url, json=payload)
        return resp.json().get("response", "")

    # ------------------------------------------------------------------ #
    # Response parsing + normalization
    # ------------------------------------------------------------------ #
    def _parse_response(self, response: str, fallback_severity: str = "medium") -> AIAnalysisResult:
        """Parse LLM output into a validated result. Tolerates markdown fences
        and surrounding prose by extracting the first JSON object."""
        data = self._extract_json(response)

        if data is None:
            # No JSON at all — salvage bullet points as recommendations.
            lines = response.strip().split("\n")
            recs = [re.sub(r"^[\-\*\d\.\)]+\s*", "", l).strip() for l in lines if l.strip().startswith(("-", "*"))]
            logger.warning(f"AI response not JSON; salvaged {len(recs)} bullet(s). Raw: {response[:200]!r}")
            return AIAnalysisResult(
                summary=response.strip()[:200] or "No analysis returned",
                root_cause="Model did not return structured output",
                severity=fallback_severity,
                recommendations=recs[:5],
                confidence=0.3,
            )

        return AIAnalysisResult(
            summary=self._as_str(data.get("summary")),
            root_cause=self._as_str(data.get("root_cause")),
            severity=self._normalize_severity(data.get("severity"), fallback_severity),
            recommendations=self._as_str_list(data.get("recommendations")),
            confidence=self._clamp_confidence(data.get("confidence")),
        )

    @staticmethod
    def _extract_json(response: str) -> Optional[Dict]:
        if not response:
            return None
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        # Strip ```json ... ``` fences.
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass
        # Grab the first balanced-looking object.
        brace = re.search(r"\{.*\}", response, re.DOTALL)
        if brace:
            try:
                return json.loads(brace.group(0))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _as_str(value) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return str(value).strip()

    @staticmethod
    def _as_str_list(value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, dict):
                    # e.g. {"step": "...", "priority": "high"}
                    out.append(" — ".join(str(v) for v in item.values()))
                else:
                    s = str(item).strip()
                    if s:
                        out.append(s)
            return out[:8]
        return [str(value).strip()]

    @staticmethod
    def _normalize_severity(value, fallback: str) -> str:
        if isinstance(value, str) and value.lower() in VALID_SEVERITIES:
            return value.lower()
        return fallback if fallback in VALID_SEVERITIES else "medium"

    @staticmethod
    def _clamp_confidence(value) -> float:
        try:
            c = float(value)
        except (TypeError, ValueError):
            return 0.5
        if c > 1.0:  # some models answer 0-100
            c = c / 100.0
        return max(0.0, min(1.0, c))

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #
    def health_check(self) -> bool:
        """Check if the active AI provider is reachable and authenticated."""
        try:
            if self.provider in HEALTH_ENDPOINTS and self.provider != "ollama-cloud":
                env_key = (
                    OPENAI_COMPATIBLE[self.provider][0]
                    if self.provider in OPENAI_COMPATIBLE
                    else "ANTHROPIC_API_KEY"
                )
                api_key = os.getenv(env_key)
                if not api_key:
                    return False
                headers = (
                    {"x-api-key": api_key}
                    if self.provider == "anthropic"
                    else {"Authorization": f"Bearer {api_key}"}
                )
                resp = requests.get(HEALTH_ENDPOINTS[self.provider], headers=headers, timeout=5)
                return resp.status_code == 200
            if self.use_cloud and self.api_key:
                resp = requests.get(
                    HEALTH_ENDPOINTS["ollama-cloud"],
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5,
                )
                return resp.status_code == 200
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"AI health check failed ({self.provider}): {e}")
            return False


def get_ollama_client() -> OllamaClient:
    """Get singleton instance."""
    if not hasattr(get_ollama_client, "_instance"):
        get_ollama_client._instance = OllamaClient()
    return get_ollama_client._instance
