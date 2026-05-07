"""
DockWatch Frontend Test Suite
Tests the frontend pages accessible via HTTP.
"""

import requests
import unittest

BASE_URL = "http://localhost:3001"

class TestFrontendHealth(unittest.TestCase):
    """Test frontend health."""

    def test_frontend_running(self):
        """Frontend is running."""
        r = requests.get(BASE_URL, timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ Frontend running")

    def test_title_correct(self):
        """Title is correct."""
        r = requests.get(BASE_URL, timeout=5)
        self.assertIn("dockwatch", r.text.lower())
        print("✅ Title correct")


class TestFrontendPages(unittest.TestCase):
    """Test frontend pages."""

    def test_login(self):
        r = requests.get(f"{BASE_URL}/login", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /login")

    def test_dashboard(self):
        r = requests.get(f"{BASE_URL}/", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /")

    def test_containers(self):
        r = requests.get(f"{BASE_URL}/containers", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /containers")

    def test_hosts(self):
        r = requests.get(f"{BASE_URL}/hosts", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /hosts")

    def test_alerts(self):
        r = requests.get(f"{BASE_URL}/alerts", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /alerts")

    def test_settings(self):
        r = requests.get(f"{BASE_URL}/settings", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /settings")

    def test_stacks(self):
        r = requests.get(f"{BASE_URL}/stacks", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /stacks")

    def test_audit(self):
        r = requests.get(f"{BASE_URL}/audit", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /audit")

    def test_users(self):
        r = requests.get(f"{BASE_URL}/users", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /users")

    def test_security(self):
        r = requests.get(f"{BASE_URL}/security", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /security")

    def test_alert_rules(self):
        r = requests.get(f"{BASE_URL}/alert-rules", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /alert-rules")

    def test_schedules(self):
        r = requests.get(f"{BASE_URL}/schedules", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /schedules")

    def test_notifications(self):
        r = requests.get(f"{BASE_URL}/notifications", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /notifications")

    def test_backup(self):
        r = requests.get(f"{BASE_URL}/backup", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /backup")

    def test_docker(self):
        r = requests.get(f"{BASE_URL}/docker", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /docker")

    def test_compare(self):
        r = requests.get(f"{BASE_URL}/compare", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /compare")

    def test_topology(self):
        r = requests.get(f"{BASE_URL}/topology", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /topology")

    def test_ai(self):
        r = requests.get(f"{BASE_URL}/ai", timeout=5)
        self.assertEqual(r.status_code, 200)
        print("✅ /ai")


class TestSecurity(unittest.TestCase):
    """Security tests."""

    def test_no_creds_exposed(self):
        r = requests.get(f"{BASE_URL}/login", timeout=5)
        self.assertNotIn("admin123", r.text)
        print("✅ No creds in HTML")

    def test_no_password_field(self):
        r = requests.get(f"{BASE_URL}/login", timeout=5)
        self.assertNotIn('value="', r.text)
        print("✅ No password values")


if __name__ == "__main__":
    print("\n🚀 Running DockWatch Tests...\n")
    unittest.main(verbosity=2)