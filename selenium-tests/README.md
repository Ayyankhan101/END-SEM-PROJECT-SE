# Selenium Login Tests — DockWatch

Automated browser tests for the DockWatch login page using Python + Selenium.

## Folder Structure

```
selenium-tests/
├── login_tests.py       # Main test file with 5 test cases
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Prerequisites

- Python 3.9+
- Google Chrome browser installed
- Your frontend dev server running at `http://localhost:5173`

## Setup

```bash
# 1. Navigate to this folder
cd selenium-tests

# 2. Install dependencies
pip install -r requirements.txt
```

This installs:
- **selenium** – browser automation library
- **pytest** – test runner
- **webdriver-manager** – automatically downloads the correct ChromeDriver (no manual setup)

## Configuration

Before running, open `login_tests.py` and update the **CONFIGURATION** block at the top:

```python
VALID_USERNAME = "admin"       # Your real username
VALID_PASSWORD = "admin123"    # Your real password
INVALID_PASSWORD = "wrongpass" # Any incorrect password
```

Also verify that the **LOCATOR REFERENCE** IDs match your frontend.  
The project uses `id="username"` for the username field (not `id="email"`).

## Running the Tests

```bash
# Run all tests (visible browser window)
pytest login_tests.py --verbose

# Run a single test
pytest login_tests.py::TestLogin::test_valid_login --verbose

# Run in headless mode (no GUI) — uncomment line 56 in login_tests.py:
#   options.add_argument("--headless")
```

### Expected Output (all passing)

```
collected 5 items

login_tests.py::TestLogin::test_valid_login PASSED
login_tests.py::TestLogin::test_invalid_password PASSED
login_tests.py::TestLogin::test_empty_fields PASSED
login_tests.py::TestLogin::test_empty_password PASSED
login_tests.py::TestLogin::test_empty_username PASSED
```

## What Each Test Checks

| # | Test               | Steps                                                                 | Pass condition                          |
|---|--------------------|-----------------------------------------------------------------------|-----------------------------------------|
| 1 | Valid Login        | Fill username + password, click Sign In                               | Dashboard heading "Fleet Overview" shows|
| 2 | Invalid Password   | Fill username + wrong password, click Sign In                         | Red error banner appears                |
| 3 | Both Empty         | Click Sign In with both fields blank                                  | Browser shows "please fill" tooltip     |
| 4 | Empty Password     | Fill username only, click Sign In                                     | Password field shows validation message |
| 5 | Empty Username     | Fill password only, click Sign In                                     | Username field shows validation message |

## Troubleshooting

| Problem                          | Fix                                                                 |
|----------------------------------|---------------------------------------------------------------------|
| `ModuleNotFoundError: No module named 'selenium'` | Run `pip install -r requirements.txt`                         |
| ChromeDriver version mismatch    | `webdriver-manager` handles this automatically                     |
| Test times out on valid login    | Check that your backend API is running and credentials are correct  |
| Test can't find an element       | Update the **LOCATOR REFERENCE** IDs in `login_tests.py`            |
