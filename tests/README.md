# DockWatch Selenium Test Suite

Automated browser tests for the DockWatch dashboard using Selenium WebDriver.

## What This Does

These tests automatically open a browser and test the DockWatch dashboard like a real user would:

- ✅ Login page loads correctly
- ✅ Login with correct credentials works
- ✅ Login with wrong password fails
- ✅ Dashboard loads after login
- ✅ Total containers count is visible
- ✅ Running containers section is visible
- ✅ Avg CPU metrics are displayed
- ✅ Logout works correctly

## Requirements

```bash
pip3 install selenium==4.18.1 webdriver-manager==4.0.1 --break-system-packages
```

## How to Run

Make sure the DockWatch containers are running first:

```bash
cd /home/maryam/END-SEM-PROJECT-SE
docker compose up -d
```

Then run the tests:

```bash
python3 tests/selenium_tests.py
```

## What You'll See

```
Ran 8 tests in 117.020s

OK

✅ Login page loaded
✅ Login successful
✅ Wrong password correctly rejected
✅ Dashboard loaded after login
✅ Total Containers section found on dashboard
✅ Running containers section found
✅ Avg CPU section found
✅ Logout works correctly
```

## How It Works

1. **Selenium WebDriver** - Opens Chrome browser automatically (headless mode = no window)
2. **Tests login** - Fills in username/password and clicks submit
3. **Tests dashboard** - Checks if containers appear and numbers are correct
4. **Reports results** - Shows ✅ for pass, ❌ for fail

## Why This Is Useful

- Catches bugs before users see them
- Tests the whole app like a real user
- Runs automatically — no manual clicking needed
- Can run in CI/CD pipelines

## Debugging

If a test fails, remove `--headless` from line 23 in `selenium_tests.py` to see the browser window and watch what happens.
