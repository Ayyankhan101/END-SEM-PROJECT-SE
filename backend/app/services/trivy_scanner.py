"""
Trivy CVE scanner service.
"""
import logging
import json
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    vuln_id: str
    severity: str
    title: str
    package: str
    installed_version: str
    fixed_version: Optional[str]
    description: str


@dataclass
class ScanResult:
    container_id: str
    image: str
    vulnerabilities: List[Vulnerability]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    scan_time: float


class TrivyScanner:
    """Scan container images for vulnerabilities using Trivy."""
    
    def __init__(self):
        self.image = "aquasec/trivy:latest"
        self.quiet = True
        self.format = "json"
    
    def scan_image(self, image: str) -> Dict:
        """Scan a container image for vulnerabilities."""
        try:
            cmd = [
                "docker", "run", "--rm",
                "-v", "/var/run/docker.sock:/var/run/docker.sock",
                self.image, "image",
                "--format", self.format,
                "--severity", "CRITICAL,HIGH,MEDIUM,LOW",
                image
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.warning(f"Trivy scan warning: {result.stderr}")
            
            return self._parse_output(result.stdout, image)
            
        except subprocess.TimeoutExpired:
            return {"error": "Scan timeout", "vulnerabilities": []}
        except FileNotFoundError:
            return {"error": "Docker not found", "vulnerabilities": []}
        except Exception as e:
            logger.error(f"Trivy scan error: {e}")
            return {"error": str(e), "vulnerabilities": []}
    
    def _parse_output(self, output: str, image: str) -> Dict:
        """Parse Trivy JSON output."""
        try:
            data = json.loads(output) if output else {}
        except json.JSONDecodeError:
            data = {}
        
        results = data.get("Results", [])
        vulnerabilities = []
        critical = high = medium = low = 0
        
        for result in results:
            for vuln in result.get("Vulnerabilities", []):
                severity = vuln.get("Severity", "UNKNOWN").upper()
                v = Vulnerability(
                    vuln_id=vuln.get("VulnerabilityID", ""),
                    severity=severity,
                    title=vuln.get("Title", ""),
                    package=vuln.get("PkgName", ""),
                    installed_version=vuln.get("InstalledVersion", ""),
                    fixed_version=vuln.get("FixedVersion"),
                    description=vuln.get("Description", "")[:200]
                )
                vulnerabilities.append(v)
                
                if severity == "CRITICAL":
                    critical += 1
                elif severity == "HIGH":
                    high += 1
                elif severity == "MEDIUM":
                    medium += 1
                elif severity == "LOW":
                    low += 1
        
        vulnerabilities.sort(key=lambda x: (
            0 if x.severity == "CRITICAL" else
            1 if x.severity == "HIGH" else
            2 if x.severity == "MEDIUM" else 3
        ))
        
        return {
            "image": image,
            "vulnerabilities": [
                {
                    "vuln_id": v.vuln_id,
                    "severity": v.severity,
                    "title": v.title,
                    "package": v.package,
                    "installed_version": v.installed_version,
                    "fixed_version": v.fixed_version,
                    "description": v.description
                }
                for v in vulnerabilities[:50]
            ],
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "low_count": low,
            "total_count": len(vulnerabilities)
        }
    
    def scan_container(self, container_id: str) -> Dict:
        """Scan a running container's image."""
        from app.services.docker_monitor import get_docker_monitor
        
        monitor = get_docker_monitor()
        if not monitor.connect():
            return {"error": "Docker not connected"}
        
        container = monitor.get_container(container_id)
        if not container:
            return {"error": "Container not found"}
        
        image = container.get("image", "")
        if not image:
            return {"error": "No image found for container"}
        
        return self.scan_image(image)


def get_trivy_scanner() -> TrivyScanner:
    """Get singleton instance."""
    if not hasattr(get_trivy_scanner, "_instance"):
        get_trivy_scanner._instance = TrivyScanner()
    return get_trivy_scanner._instance