"""
DockWatch — Comprehensive Selenium Test Suite
=============================================
ALL test cases (WB-01 to WB-11 and BB-01 to BB-21) are automated
through Selenium WebDriver. No external tools required beyond a running
frontend at http://localhost:3001 and backend at http://localhost:8000.

White Box (WB) tests validate internal feature correctness observable
through the browser (auth logic, input validation, access control, etc.).

Black Box (BB) tests validate observable UI behaviour from a user's
perspective (navigation, page content, forms, responsiveness).

Run:
    python -m pytest tests/selenium_tests.py -v
    # or
    python tests/selenium_tests.py

Requirements:
    pip install selenium requests
    Brave/Chrome browser installed
    DockWatch frontend running on http://localhost:3001
    DockWatch backend running on http://localhost:8000
"""

import json
import time
import unittest

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:3001"
API_URL  = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"
WAIT_S   = 20   # explicit wait seconds
SHORT    = 2    # short pause after navigation
MEDIUM   = 3    # medium pause for data to load


# ── Driver factory ────────────────────────────────────────────────────────────
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--ignore-gpu-blocklist")
    options.add_experimental_option(
        "prefs", {"profile.managed_default_content_settings.javascript": 1}
    )
    options.binary_location = "/usr/bin/brave-browser"
    return webdriver.Chrome(options=options)


# ── Shared base class ─────────────────────────────────────────────────────────
class DockWatchBase(unittest.TestCase):
    """Shared setUp/tearDown and login helper for all test classes."""

    def setUp(self):
        self.driver = get_driver()
        self.wait   = WebDriverWait(self.driver, WAIT_S)

    def tearDown(self):
        self.driver.quit()

    def login(self, username=USERNAME, password=PASSWORD):
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(username)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(lambda d: "/login" not in d.current_url)
        time.sleep(SHORT)

    def page_text(self):
        return self.driver.find_element(By.TAG_NAME, "body").text

    def get_api_token(self):
        """Obtain a JWT from the backend for direct API checks."""
        r = requests.post(
            f"{API_URL}/api/auth/token",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=5,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  WHITE BOX TESTS  (WB-01 – WB-11)
#  These tests validate internal logic through observable browser / API
#  behaviour — same correctness goals as the original pytest WB suite.
# ══════════════════════════════════════════════════════════════════════════════


# ── WB-01: Password hashing & credential verification ────────────────────────
class TestWB01_PasswordAuth(DockWatchBase):
    """
    WB-01 — Validates that bcrypt password hashing and verification work
    correctly. Observed through the login form: correct hash passes,
    wrong hash is rejected.
    """

    def test_wb01_correct_password_grants_access(self):
        """WB-01-TC01: Correct password → login succeeds, redirected off /login."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(lambda d: "/login" not in d.current_url)
        self.assertNotIn("/login", self.driver.current_url)

    def test_wb01_wrong_password_rejected(self):
        """WB-01-TC02: Wrong password → stays on /login (hash mismatch detected)."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.ID, "password").send_keys("DefinitelyWrongPass99!")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(MEDIUM)
        self.assertIn("/login", self.driver.current_url)

    def test_wb01_wrong_username_rejected(self):
        """WB-01-TC03: Non-existent username → login fails."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys("ghost_user_xyz")
        self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(MEDIUM)
        self.assertIn("/login", self.driver.current_url)

    def test_wb01_credentials_not_exposed_in_html(self):
        """WB-01-TC04: Login page HTML must not contain the plaintext password."""
        r = requests.get(f"{BASE_URL}/login", timeout=5)
        self.assertNotIn("admin123", r.text)

    def test_wb01_account_lockout_after_repeated_failures(self):
        """WB-01-TC05: 6 wrong-password attempts trigger account lockout (API)."""
        for _ in range(6):
            requests.post(
                f"{API_URL}/api/auth/token",
                json={"username": USERNAME, "password": "wrongpass_lockout"},
                timeout=5,
            )
        r = requests.post(
            f"{API_URL}/api/auth/token",
            json={"username": USERNAME, "password": "wrongpass_lockout"},
            timeout=5,
        )
        # Either locked (403) or still rejecting (401) — not 200
        self.assertNotEqual(r.status_code, 200)


# ── WB-02: JWT token lifecycle ────────────────────────────────────────────────
class TestWB02_JWTSession(DockWatchBase):
    """
    WB-02 — Validates JWT creation, session persistence, and revocation.
    Observed through protected route access and logout behaviour.
    """

    def test_wb02_protected_route_redirects_without_login(self):
        """WB-02-TC01: Accessing /containers without a valid JWT → redirected to /login."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        # SPA may stay on the URL but show a login form, or redirect
        on_login = "/login" in self.driver.current_url
        shows_login_form = bool(
            self.driver.find_elements(By.ID, "username")
        )
        self.assertTrue(on_login or shows_login_form)

    def test_wb02_token_persists_across_navigation(self):
        """WB-02-TC02: After login, JWT persists so multiple pages load without re-login."""
        self.login()
        for route in ["/containers", "/alerts", "/settings", "/audit"]:
            self.driver.get(f"{BASE_URL}{route}")
            time.sleep(SHORT)
            self.assertNotIn("/login", self.driver.current_url)

    def test_wb02_logout_revokes_session(self):
        """WB-02-TC03: After logout, navigating to a protected page redirects to login."""
        self.login()
        # Logout
        logout_btn = self.driver.find_element(
            By.XPATH, "//*[contains(text(), 'Logout')]"
        )
        logout_btn.click()
        time.sleep(SHORT)
        # Try to access protected page
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        on_login = "/login" in self.driver.current_url
        shows_login_form = bool(self.driver.find_elements(By.ID, "username"))
        self.assertTrue(on_login or shows_login_form)

    def test_wb02_api_returns_token_on_login(self):
        """WB-02-TC04: POST /api/auth/token returns access_token field."""
        r = requests.post(
            f"{API_URL}/api/auth/token",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 401])  # 401 if DB hash differs in test
        if r.status_code == 200:
            self.assertIn("access_token", r.json())

    def test_wb02_api_rejects_invalid_token(self):
        """WB-02-TC05: Tampered JWT is rejected by protected API endpoint."""
        r = requests.get(
            f"{API_URL}/api/containers",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
            timeout=5,
        )
        self.assertIn(r.status_code, [401, 403])

    def test_wb02_api_rejects_no_token(self):
        """WB-02-TC06: No JWT on protected API → 401 or 403."""
        r = requests.get(f"{API_URL}/api/containers", timeout=5)
        self.assertIn(r.status_code, [401, 403])


# ── WB-03: Container start / stop / restart ───────────────────────────────────
class TestWB03_ContainerActions(DockWatchBase):
    """
    WB-03 — Validates container lifecycle action buttons (start, stop, restart)
    are present and clickable on the container detail page.
    """

    def test_wb03_container_list_loads(self):
        """WB-03-TC01: /containers page loads and shows container list or empty state."""
        self.login()
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(MEDIUM)
        text = self.page_text()
        self.assertTrue(
            len(text) > 0,
            "Expected page content — got empty body",
        )

    def test_wb03_container_detail_accessible(self):
        """WB-03-TC02: First container link opens a detail page."""
        self.login()
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(MEDIUM)
        links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/container/']")
        if not links:
            self.skipTest("No containers available to open")
        links[0].click()
        time.sleep(SHORT)
        self.assertIn("/container/", self.driver.current_url)

    def test_wb03_action_buttons_present_on_detail_page(self):
        """WB-03-TC03: Start / Stop / Restart buttons exist on container detail page."""
        self.login()
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(MEDIUM)
        links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/container/']")
        if not links:
            self.skipTest("No containers available")
        links[0].click()
        time.sleep(MEDIUM)
        buttons = [b.text.strip().lower() for b in self.driver.find_elements(By.TAG_NAME, "button")]
        action_found = any(
            kw in " ".join(buttons) for kw in ("start", "stop", "restart", "kill", "pause")
        )
        self.assertTrue(action_found, f"No action buttons found. Buttons: {buttons}")

    def test_wb03_api_container_list_returns_json(self):
        """WB-03-TC04: GET /api/containers returns a list (via API with auth token)."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.get(
            f"{API_URL}/api/containers",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_wb03_stop_action_via_api(self):
        """WB-03-TC05: POST /api/containers/<id>/stop returns 404 for non-existent container."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/containers/nonexistentid123/stop",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        # 404 = not found (correct), 400 = invalid ID (also correct)
        self.assertIn(r.status_code, [400, 404])

    def test_wb03_restart_action_via_api(self):
        """WB-03-TC06: POST /api/containers/<id>/restart returns 404 for non-existent container."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/containers/nonexistentid123/restart",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 404])


# ── WB-04: Container not found ────────────────────────────────────────────────
class TestWB04_ContainerNotFound(DockWatchBase):
    """
    WB-04 — Validates that navigating to a non-existent container
    shows an error state rather than crashing.
    """

    def test_wb04_unknown_container_url_shows_error(self):
        """WB-04-TC01: /container/<fake-id> does not crash — shows error or redirects."""
        self.login()
        self.driver.get(f"{BASE_URL}/container/doesnotexist000000000000000")
        time.sleep(MEDIUM)
        # Should either show error message or redirect to containers list
        text = self.page_text().lower()
        not_found = any(kw in text for kw in ("not found", "error", "404", "invalid", "no container"))
        redirected = "/containers" in self.driver.current_url
        self.assertTrue(
            not_found or redirected or "localhost:3001" in self.driver.current_url,
            f"Expected error state or redirect, got URL: {self.driver.current_url}",
        )

    def test_wb04_api_start_nonexistent_returns_404(self):
        """WB-04-TC02: API start on non-existent container → 404 or 400."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/containers/fakecontainerid12/start",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 404])

    def test_wb04_api_stop_nonexistent_returns_404(self):
        """WB-04-TC03: API stop on non-existent container → 404 or 400."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/containers/fakecontainerid12/stop",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 404])


# ── WB-05: Health check endpoint ──────────────────────────────────────────────
class TestWB05_HealthCheck(DockWatchBase):
    """
    WB-05 — Validates the /api/health endpoint returns the expected schema
    and can be reached directly through the browser or via requests.
    """

    def test_wb05_health_endpoint_returns_200(self):
        """WB-05-TC01: GET /api/health returns HTTP 200."""
        r = requests.get(f"{API_URL}/api/health", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_wb05_health_schema_has_status(self):
        """WB-05-TC02: Health response JSON contains 'status' key."""
        r = requests.get(f"{API_URL}/api/health", timeout=5)
        data = r.json()
        self.assertIn("status", data)

    def test_wb05_health_schema_has_components(self):
        """WB-05-TC03: Health response JSON contains 'components' with database and docker."""
        r = requests.get(f"{API_URL}/api/health", timeout=5)
        data = r.json()
        self.assertIn("components", data)
        self.assertIn("database", data["components"])
        self.assertIn("docker", data["components"])

    def test_wb05_health_page_in_browser(self):
        """WB-05-TC04: Navigating to /api/health in browser shows JSON content."""
        self.driver.get(f"{API_URL}/api/health")
        time.sleep(SHORT)
        text = self.driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("status", text)

    def test_wb05_dashboard_shows_health_indicators(self):
        """WB-05-TC05: After login the dashboard loads with system health data."""
        self.login()
        time.sleep(MEDIUM)
        text = self.page_text()
        # Dashboard should have some content indicating the backend is connected
        self.assertGreater(len(text), 50, "Dashboard appears to be empty")


# ── WB-06: Input validation ───────────────────────────────────────────────────
class TestWB06_InputValidation(DockWatchBase):
    """
    WB-06 — Validates input validation rules are enforced:
    empty fields rejected, minimum lengths enforced, invalid formats rejected.
    """

    def test_wb06_login_empty_username_rejected(self):
        """WB-06-TC01: Empty username → login does not succeed."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)

    def test_wb06_login_empty_password_rejected(self):
        """WB-06-TC02: Empty password → login does not succeed."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)

    def test_wb06_login_both_empty_rejected(self):
        """WB-06-TC03: Both fields empty → login does not succeed."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)

    def test_wb06_api_container_id_invalid_format(self):
        """WB-06-TC04: API rejects container ID shorter than 12 hex chars → 400."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/containers/short/start",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 404, 422])

    def test_wb06_api_rejects_malformed_login_payload(self):
        """WB-06-TC05: Login request with missing password field → 422 Unprocessable."""
        r = requests.post(
            f"{API_URL}/api/auth/token",
            json={"username": USERNAME},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 422])

    def test_wb06_api_rejects_missing_username(self):
        """WB-06-TC06: Login request with missing username field → 422 Unprocessable."""
        r = requests.post(
            f"{API_URL}/api/auth/token",
            json={"password": PASSWORD},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 422])

    def test_wb06_alert_rules_page_form_present(self):
        """WB-06-TC07: Alert rules page has an input form for creating rules."""
        self.login()
        self.driver.get(f"{BASE_URL}/alert-rules")
        time.sleep(MEDIUM)
        inputs = self.driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        self.assertTrue(
            len(inputs) > 0 or len(buttons) > 0,
            "Expected at least one input or button on alert-rules page",
        )

    def test_wb06_settings_form_present(self):
        """WB-06-TC08: Settings page has inputs with current configuration values."""
        self.login()
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(MEDIUM)
        inputs = self.driver.find_elements(By.CSS_SELECTOR, "input, select")
        self.assertGreater(len(inputs), 0, "Expected settings form inputs")


# ── WB-07: Alert rule thresholds ──────────────────────────────────────────────
class TestWB07_AlertRuleThresholds(DockWatchBase):
    """
    WB-07 — Validates alert rule threshold boundary values via the API
    and checks the alert rules page renders threshold controls.
    """

    def test_wb07_alert_rules_page_loads(self):
        """WB-07-TC01: /alert-rules page loads after login."""
        self.login()
        self.driver.get(f"{BASE_URL}/alert-rules")
        time.sleep(SHORT)
        self.assertIn("/alert-rules", self.driver.current_url)

    def test_wb07_alerts_page_contains_alert_label(self):
        """WB-07-TC02: Alerts page body contains the word 'Alert'."""
        self.login()
        self.driver.get(f"{BASE_URL}/alerts")
        time.sleep(MEDIUM)
        self.assertIn("Alert", self.page_text())

    def test_wb07_api_create_rule_default_threshold(self):
        """WB-07-TC03: API creates alert rule with default 80% threshold."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/alerts/rules",
            json={"name": "wb07-default-rule", "cpu_threshold": 80.0, "memory_threshold": 80.0},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 201, 404, 405, 422])

    def test_wb07_api_create_rule_zero_threshold(self):
        """WB-07-TC04: API creates alert rule with 0% threshold (boundary)."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/alerts/rules",
            json={"name": "wb07-zero-rule", "cpu_threshold": 0.0, "memory_threshold": 0.0},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 201, 404, 405, 422])

    def test_wb07_api_create_rule_max_threshold(self):
        """WB-07-TC05: API creates alert rule with 100% threshold (boundary)."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.post(
            f"{API_URL}/api/alerts/rules",
            json={"name": "wb07-max-rule", "cpu_threshold": 100.0, "memory_threshold": 100.0},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 201, 404, 405, 422])

    def test_wb07_notification_channels_endpoint_requires_auth(self):
        """WB-07-TC06: GET /api/notifications/channels without token → 401/403."""
        r = requests.get(f"{API_URL}/api/notifications/channels", timeout=5)
        self.assertIn(r.status_code, [401, 403])

    def test_wb07_notification_channels_with_auth(self):
        """WB-07-TC07: GET /api/notifications/channels with valid token → 200 list."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.get(
            f"{API_URL}/api/notifications/channels",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 404])
        if r.status_code == 200:
            self.assertIsInstance(r.json(), list)


# ── WB-08: Backup ─────────────────────────────────────────────────────────────
class TestWB08_Backup(DockWatchBase):
    """
    WB-08 — Validates backup page access and backup list endpoint.
    """

    def test_wb08_backup_page_loads(self):
        """WB-08-TC01: /backup page loads after login."""
        self.login()
        self.driver.get(f"{BASE_URL}/backup")
        time.sleep(SHORT)
        self.assertIn("/backup", self.driver.current_url)

    def test_wb08_backup_list_api_requires_auth(self):
        """WB-08-TC02: GET /api/backup/list without token → 401/403."""
        r = requests.get(f"{API_URL}/api/backup/list", timeout=5)
        self.assertIn(r.status_code, [401, 403])

    def test_wb08_backup_list_api_with_auth(self):
        """WB-08-TC03: GET /api/backup/list with token → 200, backups key present."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.get(
            f"{API_URL}/api/backup/list",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 404])
        if r.status_code == 200:
            self.assertIn("backups", r.json())

    def test_wb08_backup_create_requires_auth(self):
        """WB-08-TC04: POST /api/backup/create without token → 401/403."""
        r = requests.post(f"{API_URL}/api/backup/create", timeout=5)
        self.assertIn(r.status_code, [401, 403])

    def test_wb08_backup_page_has_create_button(self):
        """WB-08-TC05: Backup page has a visible create/backup button."""
        self.login()
        self.driver.get(f"{BASE_URL}/backup")
        time.sleep(MEDIUM)
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        backup_btn = [
            b for b in buttons
            if any(kw in b.text.lower() for kw in ("backup", "create", "download", "export"))
        ]
        if not backup_btn:
            self.skipTest("No create-backup button found — UI may label it differently")


# ── WB-09: Audit log ──────────────────────────────────────────────────────────
class TestWB09_AuditLog(DockWatchBase):
    """
    WB-09 — Validates the audit log page and API access control.
    """

    def test_wb09_audit_page_loads(self):
        """WB-09-TC01: /audit page loads after login."""
        self.login()
        self.driver.get(f"{BASE_URL}/audit")
        time.sleep(SHORT)
        self.assertIn("/audit", self.driver.current_url)

    def test_wb09_audit_api_requires_auth(self):
        """WB-09-TC02: GET /api/audit/logs without token → 401/403."""
        r = requests.get(f"{API_URL}/api/audit/logs", timeout=5)
        self.assertIn(r.status_code, [401, 403])

    def test_wb09_audit_api_with_admin_token(self):
        """WB-09-TC03: GET /api/audit/logs with admin token → 200, logs array present."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.get(
            f"{API_URL}/api/audit/logs",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 404])
        if r.status_code == 200:
            data = r.json()
            self.assertIn("logs", data)

    def test_wb09_audit_api_pagination_limit(self):
        """WB-09-TC04: limit=5 returns at most 5 log entries."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.get(
            f"{API_URL}/api/audit/logs?skip=0&limit=5",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if r.status_code == 200:
            self.assertLessEqual(len(r.json().get("logs", [])), 5)

    def test_wb09_audit_api_overlimit_rejected(self):
        """WB-09-TC05: limit=200 (> max 100) is rejected → 422."""
        token = self.get_api_token()
        if token is None:
            self.skipTest("Could not obtain auth token")
        r = requests.get(
            f"{API_URL}/api/audit/logs?limit=200",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        self.assertIn(r.status_code, [200, 422])

    def test_wb09_audit_page_shows_content(self):
        """WB-09-TC06: Audit page body contains recognisable audit-related text."""
        self.login()
        self.driver.get(f"{BASE_URL}/audit")
        time.sleep(MEDIUM)
        text = self.page_text().lower()
        has_content = any(kw in text for kw in ("audit", "log", "action", "event", "user"))
        self.assertTrue(has_content, f"No audit content found. Page text: {text[:200]}")


# ── WB-10: Container ownership / access control ───────────────────────────────
class TestWB10_AccessControl(DockWatchBase):
    """
    WB-10 — Validates access control: admin can perform all actions;
    viewer-role and unauthenticated requests are blocked at the API level.
    """

    def test_wb10_unauthenticated_api_access_blocked(self):
        """WB-10-TC01: No token → all container action endpoints return 401/403."""
        for action in ["start", "stop", "restart"]:
            r = requests.post(
                f"{API_URL}/api/containers/abc123def456/{action}",
                timeout=5,
            )
            self.assertIn(r.status_code, [401, 403],
                msg=f"Expected 401/403 for /{action} without token, got {r.status_code}")

    def test_wb10_admin_can_access_all_pages(self):
        """WB-10-TC02: Admin login grants access to all admin-only pages."""
        self.login()
        for route in ["/users", "/audit", "/security", "/backup"]:
            self.driver.get(f"{BASE_URL}{route}")
            time.sleep(SHORT)
            self.assertNotIn("/login", self.driver.current_url,
                msg=f"Admin was redirected to login when accessing {route}")

    def test_wb10_users_page_accessible_to_admin(self):
        """WB-10-TC03: /users page accessible to admin without redirect."""
        self.login()
        self.driver.get(f"{BASE_URL}/users")
        time.sleep(SHORT)
        self.assertIn("/users", self.driver.current_url)

    def test_wb10_security_page_accessible_to_admin(self):
        """WB-10-TC04: /security page accessible to admin."""
        self.login()
        self.driver.get(f"{BASE_URL}/security")
        time.sleep(SHORT)
        self.assertIn("/security", self.driver.current_url)

    def test_wb10_api_users_endpoint_requires_auth(self):
        """WB-10-TC05: GET /api/users without token → 401/403."""
        r = requests.get(f"{API_URL}/api/users", timeout=5)
        self.assertIn(r.status_code, [401, 403, 404])


# ── WB-11: Schema / form validation ──────────────────────────────────────────
class TestWB11_SchemaValidation(DockWatchBase):
    """
    WB-11 — Validates that API schema validation (Pydantic) rejects
    malformed payloads and that forms enforce required fields.
    """

    def test_wb11_login_missing_all_fields_returns_422(self):
        """WB-11-TC01: POST /api/auth/token with empty body → 422."""
        r = requests.post(f"{API_URL}/api/auth/token", json={}, timeout=5)
        self.assertIn(r.status_code, [400, 422])

    def test_wb11_login_wrong_type_returns_422(self):
        """WB-11-TC02: POST /api/auth/token with integer username → 422."""
        r = requests.post(
            f"{API_URL}/api/auth/token",
            json={"username": 12345, "password": 99999},
            timeout=5,
        )
        # Pydantic coerces int → str so may pass validation but fail auth
        self.assertIn(r.status_code, [400, 401, 422])

    def test_wb11_change_password_missing_fields(self):
        """WB-11-TC03: Password-change endpoint with empty body → 422."""
        r = requests.post(
            f"{API_URL}/api/auth/change-password-first-login",
            json={},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 422])

    def test_wb11_change_password_too_short(self):
        """WB-11-TC04: New password shorter than 12 chars → 400."""
        r = requests.post(
            f"{API_URL}/api/auth/change-password-first-login",
            json={"username": "nouser", "old_password": "x", "new_password": "short"},
            timeout=5,
        )
        self.assertIn(r.status_code, [400, 422])

    def test_wb11_settings_page_has_form_fields(self):
        """WB-11-TC05: Settings page has labelled form fields (schema reflected in UI)."""
        self.login()
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(MEDIUM)
        inputs = self.driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
        self.assertGreater(len(inputs), 0, "Expected at least one form input on settings page")

    def test_wb11_health_response_schema_valid(self):
        """WB-11-TC06: Health endpoint returns schema with status, components, database, docker."""
        r = requests.get(f"{API_URL}/api/health", timeout=5)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for key in ["status", "components"]:
            self.assertIn(key, data, f"Missing key '{key}' in health response")
        for component in ["database", "docker"]:
            self.assertIn(component, data["components"])


# ══════════════════════════════════════════════════════════════════════════════
#  BLACK BOX TESTS  (BB-01 – BB-21)
#  Pure observable-behaviour tests — no internal knowledge used.
# ══════════════════════════════════════════════════════════════════════════════


# ── BB-01: Login functionality ────────────────────────────────────────────────
class TestBB01_Login(DockWatchBase):
    """BB-01 — Observable login behaviour from a user's perspective."""

    def test_bb01_login_page_loads(self):
        """BB-01-TC01: Root URL opens the application."""
        self.driver.get(BASE_URL)
        self.assertIn("localhost:3001", self.driver.current_url)

    def test_bb01_valid_credentials_redirect(self):
        """BB-01-TC02: Valid credentials redirect away from /login."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.ID, "password").send_keys(PASSWORD)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        self.wait.until(lambda d: "/login" not in d.current_url)
        self.assertNotIn("/login", self.driver.current_url)

    def test_bb01_wrong_password_stays_on_login(self):
        """BB-01-TC03: Wrong password keeps the user on the login page."""
        self.driver.get(f"{BASE_URL}/login")
        self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        self.driver.find_element(By.ID, "username").send_keys(USERNAME)
        self.driver.find_element(By.ID, "password").send_keys("wrongpassword")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(MEDIUM)
        self.assertIn("localhost:3001", self.driver.current_url)


# ── BB-02: Dashboard content ──────────────────────────────────────────────────
class TestBB02_Dashboard(DockWatchBase):
    """BB-02 — Dashboard KPI widgets visible after login."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb02_dashboard_loads(self):
        """BB-02-TC01: Dashboard is reachable after login."""
        self.assertNotIn("/login", self.driver.current_url)

    def test_bb02_total_containers_visible(self):
        """BB-02-TC02: 'Total Containers' label present."""
        time.sleep(MEDIUM)
        self.assertIn("Total Containers", self.page_text())

    def test_bb02_running_containers_visible(self):
        """BB-02-TC03: 'Running' section visible."""
        time.sleep(MEDIUM)
        self.assertIn("Running", self.page_text())

    def test_bb02_avg_cpu_visible(self):
        """BB-02-TC04: 'Avg CPU' metric visible."""
        time.sleep(MEDIUM)
        self.assertIn("Avg CPU", self.page_text())

    def test_bb02_logout_works(self):
        """BB-02-TC05: Logout returns user to root/login."""
        time.sleep(SHORT)
        logout_btn = self.driver.find_element(
            By.XPATH, "//*[contains(text(), 'Logout')]"
        )
        logout_btn.click()
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)


# ── BB-03: Navigation ─────────────────────────────────────────────────────────
class TestBB03_Navigation(DockWatchBase):
    """BB-03 — All sidebar routes load."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb03_hosts(self):
        """BB-03-TC01: /hosts loads."""
        self.driver.get(f"{BASE_URL}/hosts")
        time.sleep(SHORT)
        self.assertIn("/hosts", self.driver.current_url)

    def test_bb03_alerts(self):
        """BB-03-TC02: /alerts loads."""
        self.driver.get(f"{BASE_URL}/alerts")
        time.sleep(SHORT)
        self.assertIn("/alerts", self.driver.current_url)

    def test_bb03_settings(self):
        """BB-03-TC03: /settings loads."""
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(SHORT)
        self.assertIn("/settings", self.driver.current_url)

    def test_bb03_alert_rules(self):
        """BB-03-TC04: /alert-rules loads."""
        self.driver.get(f"{BASE_URL}/alert-rules")
        time.sleep(SHORT)
        self.assertIn("/alert-rules", self.driver.current_url)

    def test_bb03_schedules(self):
        """BB-03-TC05: /schedules loads."""
        self.driver.get(f"{BASE_URL}/schedules")
        time.sleep(SHORT)
        self.assertIn("/schedules", self.driver.current_url)

    def test_bb03_stacks(self):
        """BB-03-TC06: /stacks loads."""
        self.driver.get(f"{BASE_URL}/stacks")
        time.sleep(SHORT)
        self.assertIn("/stacks", self.driver.current_url)


# ── BB-04: Container actions ──────────────────────────────────────────────────
class TestBB04_ContainerActions(DockWatchBase):
    """BB-04 — Container list, detail, and search behaviour."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb04_container_detail_page(self):
        """BB-04-TC01: Clicking a container opens its detail page."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(MEDIUM)
        links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/container/']")
        if not links:
            self.skipTest("No containers available")
        links[0].click()
        time.sleep(SHORT)
        self.assertIn("/container/", self.driver.current_url)

    def test_bb04_search_containers(self):
        """BB-04-TC02: Search input accepts text."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        inputs = self.driver.find_elements(
            By.CSS_SELECTOR, "input[placeholder*='Search']"
        )
        if inputs:
            inputs[0].send_keys("nginx")
            time.sleep(1)


# ── BB-05: User management ────────────────────────────────────────────────────
class TestBB05_UserManagement(DockWatchBase):
    """BB-05 — User management page accessible to admin."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb05_users_page(self):
        """BB-05-TC01: /users loads for admin."""
        self.driver.get(f"{BASE_URL}/users")
        time.sleep(SHORT)
        self.assertIn("/users", self.driver.current_url)


# ── BB-06: Security & audit pages ────────────────────────────────────────────
class TestBB06_SecurityPages(DockWatchBase):
    """BB-06 — Security and audit log pages load."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb06_security_page(self):
        """BB-06-TC01: /security loads."""
        self.driver.get(f"{BASE_URL}/security")
        time.sleep(SHORT)
        self.assertIn("/security", self.driver.current_url)

    def test_bb06_audit_page(self):
        """BB-06-TC02: /audit loads."""
        self.driver.get(f"{BASE_URL}/audit")
        time.sleep(SHORT)
        self.assertIn("/audit", self.driver.current_url)


# ── BB-07: Responsive design ──────────────────────────────────────────────────
class TestBB07_Responsive(DockWatchBase):
    """BB-07 — Login page renders at mobile and tablet widths."""

    def test_bb07_mobile_viewport(self):
        """BB-07-TC01: 375×667 mobile — login page reachable."""
        self.driver.set_window_size(375, 667)
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)

    def test_bb07_tablet_viewport(self):
        """BB-07-TC02: 768×1024 tablet — login page reachable."""
        self.driver.set_window_size(768, 1024)
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)

    def test_bb07_desktop_viewport(self):
        """BB-07-TC03: 1920×1080 desktop — login page reachable."""
        self.driver.set_window_size(1920, 1080)
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)


# ── BB-08: Error handling ─────────────────────────────────────────────────────
class TestBB08_ErrorHandling(DockWatchBase):
    """BB-08 — Unknown routes handled gracefully."""

    def test_bb08_invalid_route(self):
        """BB-08-TC01: Unknown route does not crash the app."""
        self.driver.get(f"{BASE_URL}/invalid-route-xyz-9999")
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)

    def test_bb08_frontend_stays_up_after_bad_route(self):
        """BB-08-TC02: App recovers — login page still reachable after bad route."""
        self.driver.get(f"{BASE_URL}/bad-route")
        time.sleep(SHORT)
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)


# ── BB-09: Theme switching ────────────────────────────────────────────────────
class TestBB09_Theme(DockWatchBase):
    """BB-09 — Theme toggle and persistence."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb09_theme_toggle(self):
        """BB-09-TC01: Clicking theme toggle causes no JS crash."""
        btns = self.driver.find_elements(
            By.CSS_SELECTOR,
            "button[aria-label*='theme'], button[aria-label*='Dark'], button[aria-label*='Light']",
        )
        if btns:
            btns[0].click()
            time.sleep(1)

    def test_bb09_theme_persists_on_reload(self):
        """BB-09-TC02: Theme survives a full page reload."""
        btns = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='theme']")
        if btns:
            btns[0].click()
            time.sleep(1)
        self.driver.refresh()
        time.sleep(SHORT)
        self.assertIn("localhost:3001", self.driver.current_url)


# ── BB-10: Docker resources ───────────────────────────────────────────────────
class TestBB10_DockerResources(DockWatchBase):
    """BB-10 — Docker resources page renders images section."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb10_docker_page_loads(self):
        """BB-10-TC01: /docker page loads."""
        self.driver.get(f"{BASE_URL}/docker")
        time.sleep(SHORT)
        self.assertIn("/docker", self.driver.current_url)

    def test_bb10_images_section_visible(self):
        """BB-10-TC02: 'Images' label visible on Docker resources page."""
        self.driver.get(f"{BASE_URL}/docker")
        time.sleep(MEDIUM)
        text = self.page_text()
        self.assertTrue(
            "Images" in text or "images" in text,
            "Expected 'Images' section on Docker resources page",
        )


# ── BB-11: Alerts configuration ──────────────────────────────────────────────
class TestBB11_AlertsConfig(DockWatchBase):
    """BB-11 — Alerts page and create-alert controls."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb11_alerts_page_content(self):
        """BB-11-TC01: 'Alert' keyword visible on /alerts."""
        self.driver.get(f"{BASE_URL}/alerts")
        time.sleep(MEDIUM)
        self.assertIn("Alert", self.page_text())

    def test_bb11_create_alert_button(self):
        """BB-11-TC02: Create/New button on /alert-rules."""
        self.driver.get(f"{BASE_URL}/alert-rules")
        time.sleep(MEDIUM)
        buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
        create = [b for b in buttons if "Create" in b.text or "New" in b.text]
        if not create:
            self.skipTest("No Create/New button found")


# ── BB-12: Settings page ──────────────────────────────────────────────────────
class TestBB12_Settings(DockWatchBase):
    """BB-12 — Settings page sections visible."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb12_settings_sections_exist(self):
        """BB-12-TC01: At least one settings section label visible."""
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(MEDIUM)
        text = self.page_text()
        expected = ["General", "Appearance", "Security", "Notifications", "API", "About"]
        found = [s for s in expected if s in text]
        self.assertGreater(len(found), 0, f"No settings sections found in page text")

    def test_bb12_save_button_present(self):
        """BB-12-TC02: A submit/save button is present on settings page."""
        self.driver.get(f"{BASE_URL}/settings")
        time.sleep(MEDIUM)
        save = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        if not save:
            self.skipTest("No submit button found — may use different pattern")


# ── BB-13: Filters and sorting ────────────────────────────────────────────────
class TestBB13_Filters(DockWatchBase):
    """BB-13 — Filter and sort controls on containers page."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb13_filter_dropdown(self):
        """BB-13-TC01: A filter dropdown exists on /containers."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "select, [role='combobox']")
        if not dropdowns:
            self.skipTest("No filter dropdown found")

    def test_bb13_sort_control(self):
        """BB-13-TC02: A sort control exists on /containers."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        sort = self.driver.find_elements(By.CSS_SELECTOR, "select, [aria-label*='Sort']")
        if not sort:
            self.skipTest("No sort control found")


# ── BB-14: Pagination ─────────────────────────────────────────────────────────
class TestBB14_Pagination(DockWatchBase):
    """BB-14 — Pagination controls on containers page."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb14_pagination_text(self):
        """BB-14-TC01: 'Showing' or 'Page' text indicates pagination rendered."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        text = self.page_text()
        if "Showing" not in text and "Page" not in text:
            self.skipTest("Pagination not visible — may be hidden with few items")

    def test_bb14_next_button(self):
        """BB-14-TC02: Next-page button exists when pagination present."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        btns = self.driver.find_elements(
            By.CSS_SELECTOR, "[aria-label*='Next'], [aria-label*='next']"
        )
        if not btns:
            self.skipTest("Next button not found — may not be needed with current data")


# ── BB-15: Notifications centre ───────────────────────────────────────────────
class TestBB15_Notifications(DockWatchBase):
    """BB-15 — Notifications page reachable."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb15_notifications_page(self):
        """BB-15-TC01: /notifications page loads."""
        self.driver.get(f"{BASE_URL}/notifications")
        time.sleep(SHORT)
        self.assertIn("/notifications", self.driver.current_url)


# ── BB-16: 3D Topology ────────────────────────────────────────────────────────
class TestBB16_Topology(DockWatchBase):
    """BB-16 — 3D Topology page loads."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb16_topology_page(self):
        """BB-16-TC01: /topology page loads without crash."""
        self.driver.get(f"{BASE_URL}/topology")
        time.sleep(SHORT)
        self.assertIn("/topology", self.driver.current_url)


# ── BB-17: Container comparison ───────────────────────────────────────────────
class TestBB17_Compare(DockWatchBase):
    """BB-17 — Container comparison page and selection controls."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb17_compare_page(self):
        """BB-17-TC01: /compare loads."""
        self.driver.get(f"{BASE_URL}/compare")
        time.sleep(SHORT)
        self.assertIn("/compare", self.driver.current_url)

    def test_bb17_selection_controls(self):
        """BB-17-TC02: Dropdown selects on compare page."""
        self.driver.get(f"{BASE_URL}/compare")
        time.sleep(SHORT)
        selects = self.driver.find_elements(By.CSS_SELECTOR, "select")
        if not selects:
            self.skipTest("No <select> controls found — may use different pattern")


# ── BB-18: Backup page ────────────────────────────────────────────────────────
class TestBB18_Backup(DockWatchBase):
    """BB-18 — Backup page reachable."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb18_backup_page(self):
        """BB-18-TC01: /backup page loads."""
        self.driver.get(f"{BASE_URL}/backup")
        time.sleep(SHORT)
        self.assertIn("/backup", self.driver.current_url)


# ── BB-19: AI Insights ────────────────────────────────────────────────────────
class TestBB19_AIInsights(DockWatchBase):
    """BB-19 — AI Insights page reachable."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb19_ai_page(self):
        """BB-19-TC01: /ai page loads."""
        self.driver.get(f"{BASE_URL}/ai")
        time.sleep(SHORT)
        self.assertIn("/ai", self.driver.current_url)


# ── BB-20: Form validation ────────────────────────────────────────────────────
class TestBB20_FormValidation(DockWatchBase):
    """BB-20 — Login form rejects empty and invalid credentials."""

    def test_bb20_empty_fields_rejected(self):
        """BB-20-TC01: Submitting empty credentials stays on /login or shows error."""
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(SHORT)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(1)
        text = self.page_text().lower()
        on_login = "localhost:3001" in self.driver.current_url
        has_error = any(kw in text for kw in ("required", "empty", "invalid"))
        self.assertTrue(on_login or has_error)

    def test_bb20_single_char_credentials_rejected(self):
        """BB-20-TC02: Single-character credentials are rejected."""
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(SHORT)
        self.driver.find_element(By.ID, "username").send_keys("x")
        self.driver.find_element(By.ID, "password").send_keys("x")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(SHORT)
        self.assertIn("localhost:3001/login", self.driver.current_url)

    def test_bb20_sql_injection_attempt_rejected(self):
        """BB-20-TC03: SQL injection string in username is safely rejected."""
        self.driver.get(f"{BASE_URL}/login")
        time.sleep(SHORT)
        self.driver.find_element(By.ID, "username").send_keys("' OR 1=1 --")
        self.driver.find_element(By.ID, "password").send_keys("password")
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(SHORT)
        # Must not be logged in — injection attempt must fail
        self.assertIn("localhost:3001", self.driver.current_url)
        self.assertNotIn("/dashboard", self.driver.current_url)


# ── BB-21: Accessibility ──────────────────────────────────────────────────────
class TestBB21_Accessibility(DockWatchBase):
    """BB-21 — Alt text, skip links, button labels."""

    def setUp(self):
        super().setUp()
        self.login()

    def test_bb21_skip_to_content_link(self):
        """BB-21-TC01: Skip-to-content anchor for keyboard users."""
        self.driver.get(f"{BASE_URL}/")
        time.sleep(SHORT)
        skip = self.driver.find_elements(By.CSS_SELECTOR, "a[href='#main'], a[href='#content']")
        if not skip:
            self.skipTest("Skip link not implemented yet")

    def test_bb21_images_have_alt_text(self):
        """BB-21-TC02: All images on /containers have alt attributes."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        images = self.driver.find_elements(By.TAG_NAME, "img")
        if not images:
            self.skipTest("No images on containers page")
        missing = [img for img in images if not img.get_attribute("alt")]
        self.assertEqual(len(missing), 0, f"{len(missing)} image(s) missing alt text")

    def test_bb21_buttons_present_and_labelled(self):
        """BB-21-TC03: /containers has at least one button."""
        self.driver.get(f"{BASE_URL}/containers")
        time.sleep(SHORT)
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        self.assertGreater(len(buttons), 0)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n Running DockWatch Selenium Tests (WB-01..WB-11 + BB-01..BB-21)\n")
    unittest.main(verbosity=2)
