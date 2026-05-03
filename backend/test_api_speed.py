#!/usr/bin/env python3
"""
Simple test script to measure API response times.
Run this after starting the backend server to verify metrics are being collected.
"""
import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(name, path, method="get", **kwargs):
    """Test a single endpoint and return response time."""
    url = f"{BASE_URL}{path}"
    start = time.time()
    try:
        response = requests.request(method, url, **kwargs)
        elapsed = time.time() - start
        status = "✓" if response.status_code < 400 else "✗"
        print(f"{status} {name}: {response.status_code} in {elapsed:.4f}s")
        return elapsed, response.status_code
    except requests.RequestException as e:
        elapsed = time.time() - start
        print(f"✗ {name}: FAILED ({e})")
        return None, None

def main():
    print("=" * 60)
    print("DockWatch API Speed Test")
    print("=" * 60)
    
    # Wait for server
    print("\n[*] Checking server availability...")
    for _ in range(5):
        try:
            response = requests.get(f"{BASE_URL}/", timeout=2)
            print(f"✓ Server is up (status: {response.status_code})")
            break
        except requests.RequestException:
            print("✗ Server not responding, waiting...")
            time.sleep(2)
    else:
        print("[!] Server is not running. Start it with: cd backend && python -m app.main")
        return
    
    print("\n[*] Running speed tests...\n")
    
    times = []
    
    # Test health endpoints
    t, s = test_endpoint("Health check", "/api/health")
    if t: times.append(t)
    
    # Test API endpoints
    t, s = test_endpoint("List containers", "/api/containers")
    if t: times.append(t)
    
    t, s = test_endpoint("List volumes", "/api/volumes")
    if t: times.append(t)
    
    t, s = test_endpoint("List images", "/api/images")
    if t: times.append(t)
    
    t, s = test_endpoint("System stats", "/api/stats")
    if t: times.append(t)
    
    t, s = test_endpoint("Simple metrics", "/api/metrics/simple")
    if t: times.append(t)
    
    t, s = test_endpoint("Performance metrics", "/api/metrics/performance")
    if t: times.append(t)
    
    # Test root
    t, s = test_endpoint("Root info", "/")
    if t: times.append(t)
    
    # Summary
    if times:
        avg = sum(times) / len(times)
        print(f"\n{'=' * 60}")
        print(f"Average response time: {avg:.4f}s")
        print(f"Fastest: {min(times):.4f}s")
        print(f"Slowest: {max(times):.4f}s")
        print(f"Total endpoints tested: {len(times)}")
        print(f"{'=' * 60}")
        
        # Check X-Process-Time header
        print("\n[*] Checking response headers...")
        r = requests.get(f"{BASE_URL}/api/health")
        if "X-Process-Time-Seconds" in r.headers:
            print(f"✓ X-Process-Time-Seconds header present: {r.headers['X-Process-Time-Seconds']}s")
        else:
            print("✗ X-Process-Time-Seconds header missing")
    
    print("\n[*] You can also view full metrics at: http://localhost:8000/api/metrics/performance")

if __name__ == "__main__":
    main()
