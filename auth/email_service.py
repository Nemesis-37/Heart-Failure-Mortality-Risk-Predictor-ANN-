"""
auth/email_service.py
=====================
Email OTP delivery and cryptographic verification service.

Security Standards:
- Six-digit OTP generated via cryptographically secure pseudo-random number generator (secrets module).
- OTP is hashed before persistence; plain text is never stored in the database.
- 5-minute expiration window.
- 5 maximum verification attempts per OTP.
- 45-second resend cooldown to protect SMTP infrastructure and prevent abuse.
- SMTP delivery configured via environment variables with TLS encryption.
"""

import hashlib
import hmac
import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load settings from root .env
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# SMTP Settings
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or "587")
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "no-reply@cardiopredict.org").strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "CardioPredict Portal").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "yes").strip().lower() in ("yes", "true", "1")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 45


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(6))


def hash_otp(raw_otp: str) -> str:
    """
    Hash a 6-digit OTP with SHA-256 and salt.
    Never persist the plain 6-digit token in the database.
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", raw_otp.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"$otp$v=1${salt}${key.hex()}"


def verify_otp_hash(raw_otp: str, stored_hash: str) -> bool:
    """Verify raw OTP entry against stored PBKDF2 hash using constant-time comparison."""
    if not stored_hash or not stored_hash.startswith("$otp$v=1$"):
        return False
    try:
        parts = stored_hash.split("$")
        salt = parts[3]
        expected_hex = parts[4]
        key = hashlib.pbkdf2_hmac(
            "sha256", raw_otp.strip().encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception as exc:
        logger.warning(f"Error during OTP hash check: {exc}")
        return False


def send_email_otp(recipient_email: str, recipient_name: str, otp_code: str) -> Tuple[bool, str]:
    """
    Deliver the 6-digit verification code to the doctor's email.
    If SMTP server is configured, delivers real email.
    If running locally without SMTP credentials, logs the delivery safely.
    """
    subject = f"{otp_code} is your CardioPredict Verification Code"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Email Verification</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F3F7FC; margin: 0; padding: 24px; }}
        .email-container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #DBEAFE; overflow: hidden; }}
        .email-header {{ background: linear-gradient(135deg, #0B1F3A 0%, #102F56 50%, #1565D8 100%); color: #ffffff; padding: 28px 24px; text-align: center; }}
        .email-body {{ padding: 28px 24px; color: #1e293b; line-height: 1.6; }}
        .otp-box {{ background: #EFF6FF; border: 2px dashed #93C5FD; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }}
        .otp-code {{ font-family: Consolas, monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #1565D8; margin: 0; }}
        .email-footer {{ background: #F8FAFC; padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #E2E8F0; }}
      </style>
    </head>
    <body>
      <div class="email-container">
        <div class="email-header">
          <h2 style="margin: 0; font-size: 20px;">CardioPredict Clinical Portal</h2>
          <p style="margin: 6px 0 0; opacity: 0.85; font-size: 13px;">Physician Credential Verification</p>
        </div>
        <div class="email-body">
          <p>Dear <strong>{recipient_name}</strong>,</p>
          <p>Thank you for registering your clinical credentials. To verify your email address, please enter this one-time verification code:</p>
          <div class="otp-box">
            <p class="otp-code">{otp_code}</p>
          </div>
          <p style="font-size: 13px; color: #64748b;">
            • This code expires in <strong>5 minutes</strong>.<br>
            • Never share this code with anyone. CardioPredict staff will never ask for your code.<br>
            • If you did not initiate this registration, you can safely ignore this email.
          </p>
        </div>
        <div class="email-footer">
          Heart Failure Mortality Risk Predictor &bull; Educational Clinical Decision Support Prototype
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = (
        f"Dear {recipient_name},\n\n"
        f"Your CardioPredict verification code is: {otp_code}\n\n"
        f"This code will expire in 5 minutes.\n"
        f"If you did not request this verification, please ignore this email."
    )

    # Deliver via SMTP if configured
    if SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            msg["To"] = recipient_email

            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()

            logger.info(f"Verification email dispatched via SMTP to {recipient_email}")
            return True, "Verification email sent successfully."
        except Exception as exc:
            logger.error(f"SMTP dispatch failed: {exc}")
            # Fallback to local development log
            if APP_ENV == "development":
                logger.info(f"[DEV MODE DISPATCH] To: {recipient_email} | OTP: {otp_code}")
                return True, "Dev Mode: Verification code generated and logged."
            return False, f"Email delivery failed: {str(exc)}"

    # If no SMTP configured, use development delivery log
    logger.info(f"[LOCAL DEV SMTP SIMULATION] Verification email dispatched to: {recipient_email}")
    logger.info(f"[LOCAL DEV SMTP SIMULATION] Code: {otp_code} (Valid for 5 mins)")
    return True, "Verification code sent (Local development simulation active)."
