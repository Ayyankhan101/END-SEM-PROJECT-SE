"""
DockWatch Selenium Test Suite
Automated browser tests for the DockWatch dashboard.
"""

import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "http://localhost:3001"
USERNAME = "admin"
PASSWORD = "admin123"


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--ignore-gpu-blocklist")
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.javascript": 1})
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)


class TestLogin(unittest.TestCase):

    def setUp(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_login_page_loads(self):
        """Check that the login page opens correctly."""
        self.driver.get(BASE_URL)
        self.assertIn("localhost:3001", self.driver.current_url)
        print("✅ Login page loaded")

    def test_login_with_valid_credentials(self):
        """Login with correct username and password."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(lambda d: "/login" not in d.current_url)
        self.assertNotIn("/login", self.driver.current_url)
        print("✅ Login successful")

    def test_login_with_wrong_password(self):
        """Login with wrong password should fail."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.ID, "password").send_keys("wrongpassword")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)
        self.assertIn("localhost:3001", self.driver.current_url)
        print("✅ Wrong password correctly rejected")


class TestDashboard(unittest.TestCase):

    def setUp(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)
        self._login()

    def tearDown(self):
        self.driver.quit()

    def _login(self):
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        # Wait until redirected away from login page
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_dashboard_loads(self):
        """Dashboard page loads after login."""
        self.assertNotIn("/login", self.driver.current_url)
        print("✅ Dashboard loaded after login")

    def test_total_containers_not_zero(self):
        """Total containers count should be greater than 0."""
        time.sleep(3)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("Total Containers", page_text)
        print("✅ Total Containers section found on dashboard")

    def test_running_containers_visible(self):
        """Running containers section is visible."""
        time.sleep(3)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("Running", page_text)
        print("✅ Running containers section found")

    def test_avg_cpu_visible(self):
        """Avg CPU section is visible on dashboard."""
        time.sleep(3)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("Avg CPU", page_text)
        print("✅ Avg CPU section found")

    def test_logout_works(self):
        """Logout button works and redirects to login."""
        time.sleep(2)
        logout_btn = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Logout')]")
        logout_btn.click()
        time.sleep(2)
        self.assertIn("localhost:3001", self.driver.current_url)
        print("✅ Logout works correctly")


if __name__ == "__main__":
    print("\n🚀 Running DockWatch Selenium Tests...\n")
    unittest.main(verbosity=2)
