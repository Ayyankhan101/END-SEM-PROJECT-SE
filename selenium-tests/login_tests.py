"""
Selenium Login Test Suite — DockWatch

A comprehensive set of Selenium WebDriver tests for the DockWatch login page.
Covers valid login, invalid password, and empty-field validation scenarios.

Usage:
    pytest login_tests.py --verbose

Requirements (install once):
    pip install selenium pytest webdriver-manager
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# CONFIGURATION — Replace these values with YOUR project's credentials
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:5173"
VALID_USERNAME = "admin"       # Replace with a real username in your system
VALID_PASSWORD = "admin123"    # Replace with the correct password
INVALID_PASSWORD = "wrongpass"

# Expected page title / heading text after successful login
DASHBOARD_INDICATOR = "Fleet Overview"

# ---------------------------------------------------------------------------
# LOCATOR REFERENCE
# Update these if your project uses different element IDs / selectors.
#
#   Element              Actual ID    Notes
#   ----------------------------------------------
#   Username input        "username"   (NOT "email")
#   Password input        "password"
#   Submit button         —            Located by type="submit" + text "Sign In"
#   Error message         —            <div class="...text-red-500...">
#   Dashboard heading     —            Contains text "Fleet Overview"
#
# If your frontend uses different IDs, change the By.ID strings below.
# ---------------------------------------------------------------------------

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def driver():
    """
    Set up a fresh Chrome browser for every test.

    - Installs ChromeDriver automatically (no manual driver management).
    - Opens the login page.
    - Clears localStorage so no stale auth token remains between tests.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1280,720")
    # ── Uncomment the next line to run Chrome in headless mode ──
    # options.add_argument("--headless")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Start each test on the login page with a clean slate
    driver.get(BASE_URL + "/login")
    driver.execute_script("localStorage.clear();")
    driver.get(BASE_URL + "/login")

    yield driver

    driver.quit()


# ── Helper methods ──────────────────────────────────────────────────────────


def wait_for_element(driver, by, value, timeout=10):
    """Return an element once it is visible on the page."""
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((by, value))
    )


def fill_input(driver, by, value, text):
    """Clear an input field and type the given text into it."""
    field = wait_for_element(driver, by, value)
    field.clear()
    if text:
        field.send_keys(text)
    return field


def click_submit(driver):
    """Find and click the 'Sign In' submit button."""
    btn = wait_for_element(driver, By.XPATH, "//button[@type='submit']")
    btn.click()
    return btn


def get_validation_message(driver, by, value):
    """
    Return the native HTML5 validation message shown for a required field.
    Returns an empty string if the field is considered valid.
    """
    element = driver.find_element(by, value)
    return driver.execute_script("return arguments[0].validationMessage;", element)


# ── Test cases ──────────────────────────────────────────────────────────────


class TestLogin:

    # ────────────────────────────────────────────────────────────────────────
    # TEST 1 — Valid Login
    #
    # What it does:
    #   1. Enters a valid username and password
    #   2. Clicks "Sign In"
    #   3. Waits for the browser to navigate to the dashboard
    #   4. Asserts that the Dashboard heading ("Fleet Overview") is visible
    #
    # Pass condition: User lands on the Dashboard after login.
    # ────────────────────────────────────────────────────────────────────────
    def test_valid_login(self, driver):
        # Arrange
        fill_input(driver, By.ID, "username", VALID_USERNAME)
        fill_input(driver, By.ID, "password", VALID_PASSWORD)

        # Act
        click_submit(driver)

        # Assert — dashboard heading appears, proving we navigated to /
        heading = wait_for_element(driver, By.XPATH,
                                   f"//*[text()='{DASHBOARD_INDICATOR}']",
                                   timeout=15)
        assert heading.is_displayed(), \
            f"Expected dashboard heading '{DASHBOARD_INDICATOR}' to be visible"

    # ────────────────────────────────────────────────────────────────────────
    # TEST 2 — Invalid Password
    #
    # What it does:
    #   1. Enters a valid username with an incorrect password
    #   2. Clicks "Sign In"
    #   3. Waits for the red error banner to appear
    #   4. Asserts the error message is non-empty
    #
    # Pass condition: An error message is displayed to the user.
    # ────────────────────────────────────────────────────────────────────────
    def test_invalid_password(self, driver):
        # Arrange
        fill_input(driver, By.ID, "username", VALID_USERNAME)
        fill_input(driver, By.ID, "password", INVALID_PASSWORD)

        # Act
        click_submit(driver)

        # Assert — error banner appears (classes: text-red-500, bg-red-500/10)
        error_div = wait_for_element(driver, By.CSS_SELECTOR,
                                     "div[class*='text-red-500']",
                                     timeout=10)
        error_text = error_div.text.strip()
        assert error_text, \
            f"Expected a non-empty error message, got '{error_text}'"

    # ────────────────────────────────────────────────────────────────────────
    # TEST 3 — Both Fields Empty  (HTML5 required validation)
    #
    # What it does:
    #   1. Leaves both username and password blank
    #   2. Clicks "Sign In"
    #   3. Checks the browser's native validation message on the username field
    #      (the browser stops submission because the first required field is
    #       empty)
    #
    # Pass condition: The username input triggers a "Please fill out this
    # field" (or equivalent) validation message.
    # ────────────────────────────────────────────────────────────────────────
    def test_empty_fields(self, driver):
        # Act
        click_submit(driver)

        # Assert — browser refuses to submit; username field shows validation
        msg = get_validation_message(driver, By.ID, "username")
        assert msg, \
            "Expected a browser validation message for the empty username field"

    # ────────────────────────────────────────────────────────────────────────
    # TEST 4 — Empty Password Only
    #
    # What it does:
    #   1. Fills in the username but leaves password blank
    #   2. Clicks "Sign In"
    #   3. Checks the native validation message on the password field
    #
    # Pass condition: The password field triggers its validation message.
    # ────────────────────────────────────────────────────────────────────────
    def test_empty_password(self, driver):
        # Arrange
        fill_input(driver, By.ID, "username", VALID_USERNAME)

        # Act
        click_submit(driver)

        # Assert — password field shows validation message
        msg = get_validation_message(driver, By.ID, "password")
        assert msg, \
            "Expected a browser validation message for the empty password field"

    # ────────────────────────────────────────────────────────────────────────
    # TEST 5 — Empty Username Only
    #
    # What it does:
    #   1. Fills in the password but leaves username blank
    #   2. Clicks "Sign In"
    #   3. Checks the native validation message on the username field
    #
    # Pass condition: The username field triggers its validation message.
    # ────────────────────────────────────────────────────────────────────────
    def test_empty_username(self, driver):
        # Arrange
        fill_input(driver, By.ID, "password", VALID_PASSWORD)

        # Act
        click_submit(driver)

        # Assert — username field shows validation message
        msg = get_validation_message(driver, By.ID, "username")
        assert msg, \
            "Expected a browser validation message for the empty username field"


# ── Standalone runner (optional: run with `python login_tests.py`) ──────────

if __name__ == "__main__":
    pytest.main([__file__, "--verbose", "--capture=no"])
