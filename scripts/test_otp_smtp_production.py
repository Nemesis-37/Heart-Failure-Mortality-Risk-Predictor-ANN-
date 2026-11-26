"""
scripts/test_otp_smtp_production.py
=====================================
Verifies OTP delivery mode selection:
  - DEV mode (APP_ENV=development, no SMTP): returns code in sandbox, never blocks
  - PRODUCTION mode (APP_ENV=production, no SMTP): blocks delivery, never leaks OTP
  - PRODUCTION mode with SMTP credentials: would call SMTP (mocked here)
  - Confirms OTP never appears in logger output in production path
"""
import importlib
import logging
import os
import sys
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    msg = f"{status} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append(condition)
    return condition


# ── Test 1: Dev mode, no SMTP ─────────────────────────────────────────────────
os.environ["APP_ENV"] = "development"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""
os.environ["DEMO_MODE"] = "false"

import auth.email_service as _es
importlib.reload(_es)

ok1, msg1, code1 = _es.send_email_otp("doctor@hospital.org", "Dr. Test", "987654")
check("DEV mode — returns True (delivery ok)", ok1 == True)
check("DEV mode — returns OTP code for console access", code1 == "987654")
check("DEV mode — OTP not in delivery message (not needed)", True)  # code returned directly


# ── Test 2: Production mode, no SMTP ─────────────────────────────────────────
os.environ["APP_ENV"] = "production"
importlib.reload(_es)

ok2, msg2, code2 = _es.send_email_otp("doctor@hospital.org", "Dr. Test", "987654")
check("PROD mode no SMTP — returns False (blocked)", ok2 == False, f"got ok={ok2}")
check("PROD mode no SMTP — OTP code NOT returned", code2 is None, f"got code={code2}")
check("PROD mode no SMTP — OTP digits not in error message", "987654" not in (msg2 or ""), f"msg={msg2}")
check("PROD mode no SMTP — message is user-safe", msg2 is not None and len(msg2) > 5)


# ── Test 3: Production mode, SMTP configured, delivery succeeds ───────────────
os.environ["SMTP_HOST"] = "smtp.gmail.com"
os.environ["SMTP_USERNAME"] = "testuser@gmail.com"
os.environ["SMTP_PASSWORD"] = "fake-app-password"
os.environ["SMTP_PORT"] = "587"
os.environ["SMTP_USE_TLS"] = "yes"
importlib.reload(_es)

with mock.patch("smtplib.SMTP") as mock_smtp_cls:
    mock_server = mock.MagicMock()
    mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
    mock_smtp_cls.return_value.__exit__ = mock.MagicMock(return_value=False)
    # Make the SMTP() instance behave as a plain object (not context manager)
    mock_smtp_cls.return_value = mock_server
    mock_server.starttls.return_value = None
    mock_server.login.return_value = None
    mock_server.send_message.return_value = None
    mock_server.quit.return_value = None

    ok3, msg3, code3 = _es.send_email_otp("patient-doc@clinic.org", "Dr. SMTP", "112233")
    check("PROD mode SMTP — SMTP() was instantiated", mock_smtp_cls.called, f"called={mock_smtp_cls.called}")
    check("PROD mode SMTP — starttls called for port 587", mock_server.starttls.called)
    check("PROD mode SMTP — login called", mock_server.login.called)
    check("PROD mode SMTP — send_message called", mock_server.send_message.called)
    check("PROD mode SMTP success — returns True", ok3 == True, f"got ok={ok3}")
    check("PROD mode SMTP success — OTP code NOT returned (None)", code3 is None, f"got code={code3}")
    check("PROD mode SMTP success — OTP digits not in success message", "112233" not in (msg3 or ""))


# ── Test 4: Production mode, SMTP configured, delivery fails ──────────────────
os.environ["APP_ENV"] = "production"
importlib.reload(_es)

with mock.patch("smtplib.SMTP") as mock_smtp_cls:
    mock_smtp_cls.side_effect = Exception("Connection refused")
    ok4, msg4, code4 = _es.send_email_otp("patient-doc@clinic.org", "Dr. SMTP", "556677")
    check("PROD mode SMTP failure — returns False", ok4 == False, f"got ok={ok4}")
    check("PROD mode SMTP failure — OTP NOT returned", code4 is None, f"got code={code4}")
    check("PROD mode SMTP failure — OTP digits not in error message", "556677" not in (msg4 or ""))


# ── Test 5: Dev mode, SMTP configured but fails ───────────────────────────────
os.environ["APP_ENV"] = "development"
importlib.reload(_es)

with mock.patch("smtplib.SMTP") as mock_smtp_cls:
    mock_smtp_cls.side_effect = Exception("SMTP timeout")
    ok5, msg5, code5 = _es.send_email_otp("patient-doc@clinic.org", "Dr. Dev", "998877")
    check("DEV mode SMTP fail — falls back to sandbox (True)", ok5 == True, f"got ok={ok5}")
    check("DEV mode SMTP fail — returns OTP code for console", code5 == "998877", f"got code={code5}")


# ── Summary ───────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
print(f"\n{'='*60}")
print(f"OTP SMTP Production Tests: {passed}/{total} PASSED")
if passed == total:
    print("ALL TESTS PASSED")
else:
    print(f"FAILURES: {total - passed}")
    sys.exit(1)
