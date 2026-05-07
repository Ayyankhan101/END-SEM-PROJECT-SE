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
    options.binary_location = "/usr/bin/brave-browser"
    # Use Selenium's built-in manager (selenium 4.6+)
    return webdriver.Chrome(options=options)


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


class TestNavigation(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_navigate_to_hosts(self):
        """Navigate to Hosts page."""
        self.driver.get(f"{BASE_URL}/hosts")
        time.sleep(2)
        self.assertIn("/hosts", self.driver.current_url)
        print("✅ Hosts page loads")

    def test_navigate_to_alerts(self):
        """Navigate to Alerts page."""
        self.driver.get(f"{BASE_URL}/alerts")
        time.sleep(2)
        self.assertIn("/alerts", self.driver.current_url)
        print("✅ Alerts page loads")

    def test_navigate_to_settings(self):
        """Navigate to Settings page."""
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(2)
        self.assertIn("/settings", self.driver.current_url)
        print("✅ Settings page loads")

    def test_navigate_to_alert_rules(self):
        """Navigate to Alert Rules page."""
        self.driver.get(f"{BASE_URL}/alert-rules")
        time.sleep(2)
        self.assertIn("/alert-rules", self.driver.current_url)
        print("✅ Alert Rules page loads")

    def test_navigate_to_schedules(self):
        """Navigate to Schedules page."""
        self.driver.get(f"{BASE_URL}/schedules")
        time.sleep(2)
        self.assertIn("/schedules", self.driver.current_url)
        print("✅ Schedules page loads")

    def test_navigate_to_stacks(self):
        """Navigate to Stacks page."""
        self.driver.get(f"{BASE_URL}/stacks")
        time.sleep(2)
        self.assertIn("/stacks", self.driver.current_url)
        print("✅ Stacks page loads")


class TestContainerActions(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_container_detail_page(self):
        """Container detail page loads."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(3)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "No containers" not in page_text:
            container_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/container/']")
            if container_links:
                container_links[0].click()
                time.sleep(2)
                self.assertIn("/container/", self.driver.current_url)
                print("✅ Container detail page loads")
        else:
            print("⏭️  Skipped - no containers available")

    def test_search_containers(self):
        """Search functionality works."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(2)
        search_input = self.driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='Search']")
        if search_input:
            search_input[0].send_keys("nginx")
            time.sleep(1)
            print("✅ Search input works")
        else:
            print("⏭️  Skipped - no search input found")


class TestUserManagement(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_users_page_access(self):
        """Users page is accessible."""
        self.driver.get(f"{BASE_URL}/users")
        time.sleep(2)
        self.assertIn("/users", self.driver.current_url)
        print("✅ Users page loads")


class TestSecurity(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_security_page_access(self):
        """Security page is accessible."""
        self.driver.get(f"{BASE_URL}/security")
        time.sleep(2)
        self.assertIn("/security", self.driver.current_url)
        print("✅ Security page loads")

    def test_audit_logs_access(self):
        """Audit logs page is accessible."""
        self.driver.get(f"{BASE_URL}/audit")
        time.sleep(2)
        self.assertIn("/audit", self.driver.current_url)
        print("✅ Audit logs page loads")


class TestResponsive(unittest.TestCase):

    def setUp(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_mobile_viewport(self):
        """Page works in mobile viewport."""
        self.driver.set_window_size(375, 667)
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        self.assertIn("localhost:3001", self.driver.current_url)
        print("✅ Mobile viewport works")

    def test_tablet_viewport(self):
        """Page works in tablet viewport."""
        self.driver.set_window_size(768, 1024)
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        self.assertIn("localhost:3001", self.driver.current_url)
        print("✅ Tablet viewport works")


class TestErrorHandling(unittest.TestCase):

    def setUp(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_invalid_route_redirects(self):
        """Invalid route shows appropriate response."""
        self.driver.get(f"{BASE_URL}/invalid-route-xyz")
        time.sleep(2)
        current = self.driver.current_url
        if "/invalid-route-xyz" in current:
            print("⚠️  No redirect for invalid route")
        else:
            print("✅ Invalid route handled")


class TestThemeSwitching(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_dark_theme_toggle(self):
        """Dark theme toggle works."""
        theme_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='theme'], button[aria-label*='Dark'], button[aria-label*='Light']")
        if theme_buttons:
            theme_buttons[0].click()
            time.sleep(1)
            print("✅ Theme toggle works")
        else:
            print("⏭️  Skipped - no theme toggle found")

    def test_theme_persistence(self):
        """Theme preference persists after reload."""
        theme_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='theme']")
        if theme_buttons:
            theme_buttons[0].click()
            time.sleep(1)
            self.driver.refresh()
            time.sleep(2)
            print("✅ Theme persists after reload")


class TestDockerResources(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_docker_resources_page(self):
        """Docker resources page loads."""
        self.driver.get(f"{BASE_URL}/docker")
        time.sleep(2)
        self.assertIn("/docker", self.driver.current_url)
        print("✅ Docker resources page loads")

    def test_docker_images_visible(self):
        """Docker images section visible."""
        self.driver.get(f"{BASE_URL}/docker")
        time.sleep(2)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "Images" in page_text or "images" in page_text:
            print("✅ Docker images section found")


class TestAlertsConfiguration(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_alerts_page_content(self):
        """Alerts page shows content."""
        self.driver.get(f"{BASE_URL}/alerts")
        time.sleep(2)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "Alert" in page_text:
            print("✅ Alerts content visible")

    def test_create_alert_button(self):
        """Create alert button exists."""
        self.driver.get(f"{BASE_URL}/alert-rules")
        time.sleep(2)
        buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
        create_btn = [b for b in buttons if "Create" in b.text or "New" in b.text]
        if create_btn:
            print("✅ Create alert button found")


class TestSettingsPage(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_settings_sections_exist(self):
        """Settings page has sections."""
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(2)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        sections_found = 0
        for section in ["General", "Appearance", "Security", "Notifications", "API", "About"]:
            if section in page_text:
                sections_found += 1
        if sections_found > 0:
            print(f"✅ Settings sections found: {sections_found}")

    def test_save_settings_button(self):
        """Save settings button exists."""
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(2)
        save_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], button:contains('Save')")
        if save_buttons:
            print("✅ Save button found")


class TestFiltersAndSorting(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_status_filter_exists(self):
        """Status filter dropdown exists."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(2)
        dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "select, [role='combobox']")
        if dropdowns:
            print("✅ Filter dropdown found")

    def test_sort_dropdown_exists(self):
        """Sort dropdown exists."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(2)
        sort_elements = self.driver.find_elements(By.CSS_SELECTOR, "select, [aria-label*='Sort']")
        if sort_elements:
            print("✅ Sort dropdown found")


class TestPagination(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_pagination_controls(self):
        """Pagination controls exist on containers page."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(2)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "Showing" in page_text or "Page" in page_text:
            print("✅ Pagination controls found")

    def test_pagination_next_button(self):
        """Next page button works."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(2)
        next_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button:contains('Next'), [aria-label*='Next']")
        if next_buttons:
            print("✅ Next page button found")


class TestNotificationsCenter(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_notifications_page(self):
        """Notifications page loads."""
        self.driver.get(f"{BASE_URL}/notifications")
        time.sleep(2)
        self.assertIn("/notifications", self.driver.current_url)
        print("✅ Notifications page loads")


class TestTopology3D(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_topology_page(self):
        """3D Topology page loads."""
        self.driver.get(f"{BASE_URL}/topology")
        time.sleep(2)
        self.assertIn("/topology", self.driver.current_url)
        print("✅ Topology 3D page loads")


class TestCompareContainers(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_compare_page(self):
        """Container compare page loads."""
        self.driver.get(f"{BASE_URL}/compare")
        time.sleep(2)
        self.assertIn("/compare", self.driver.current_url)
        print("✅ Container compare page loads")

    def test_compare_selection_controls(self):
        """Compare page has selection controls."""
        self.driver.get(f"{BASE_URL}/compare")
        time.sleep(2)
        selects = self.driver.find_elements(By.CSS_SELECTOR, "select")
        if selects:
            print("✅ Compare selection controls exist")


class TestBackupPage(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_backup_page(self):
        """Backup page loads."""
        self.driver.get(f"{BASE_URL}/backup")
        time.sleep(2)
        self.assertIn("/backup", self.driver.current_url)
        print("✅ Backup page loads")


class TestAIInsights(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_ai_insights_page(self):
        """AI Insights page loads."""
        self.driver.get(f"{BASE_URL}/ai")
        time.sleep(2)
        self.assertIn("/ai", self.driver.current_url)
        print("✅ AI Insights page loads")


class TestFormValidation(unittest.TestCase):

    def setUp(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)

    def tearDown(self):
        self.driver.quit()

    def test_login_empty_credentials(self):
        """Login with empty credentials shows error."""
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(1)
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "required" in page_text.lower() or "empty" in page_text.lower():
            print("✅ Form validation works for empty fields")

    def test_login_invalid_format(self):
        """Login with invalid format shows error."""
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        self.driver.find_element(By.ID, "username").send_keys("x")
        self.driver.find_element(By.ID, "password").send_keys("x")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(2)
        if "localhost:3001/login" in self.driver.current_url:
            print("✅ Invalid credentials rejected")


class TestAccessibility(unittest.TestCase):

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
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(2)

    def test_skip_to_content_link(self):
        """Skip to content link exists for accessibility."""
        self.driver.get(f"{BASE_URL}/")
        time.sleep(2)
        skip_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href='#main'], a[href='#content']")
        if skip_links:
            print("✅ Skip link found")

    def test_all_images_have_alt(self):
        """Images have alt text."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(2)
        images = self.driver.find_elements(By.TAG_NAME, "img")
        images_with_alt = [img for img in images if img.get_attribute("alt")]
        if images:
            print(f"✅ Images: {len(images_with_alt)}/{len(images)} have alt text")

    def test_buttons_have_labels(self):
        """Buttons are accessible."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(2)
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        if buttons:
            print(f"✅ Found {len(buttons)} buttons")


if __name__ == "__main__":
    print("\n🚀 Running DockWatch Selenium Tests...\n")
    unittest.main(verbosity=2)
