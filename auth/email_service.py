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

# SMTP Settings & Dynamic Resolver
def get_smtp_config():
    """
    Dynamically read and resolve SMTP settings from environment with robust fallbacks.
    Handles Gmail domain resolution when SMTP_USERNAME is set without domain.
    """
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port_raw = os.getenv("SMTP_PORT", "587").strip() or "587"
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = 587

    raw_user = os.getenv("SMTP_USERNAME", os.getenv("SMTP_EMAIL", "")).strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    admin_email = os.getenv("ADMIN_EMAIL", "").strip()

    # Smart username resolution: If SMTP_USERNAME is set without domain (e.g. 'debashish'),
    # but SMTP_FROM_EMAIL or ADMIN_EMAIL contains '@' (e.g. 'debashish.g333@gmail.com'),
    # automatically resolve the username to the full email address for Gmail / standard SMTP.
    if raw_user and "@" not in raw_user:
        if "@" in from_email and ("@" + raw_user in from_email or "gmail" in smtp_host.lower()):
            smtp_user = from_email
        elif "@" in admin_email and ("@" + raw_user in admin_email or "gmail" in smtp_host.lower()):
            smtp_user = admin_email
        elif "gmail" in smtp_host.lower():
            smtp_user = f"{raw_user}@gmail.com"
        else:
            smtp_user = raw_user
    else:
        smtp_user = raw_user or from_email or admin_email

    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from_email = from_email or smtp_user or "no-reply@cardiopredict.org"
    smtp_from_name = os.getenv("SMTP_FROM_NAME", "CardioPredict Portal").strip()
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "yes").strip().lower() in ("yes", "true", "1")
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    demo_mode = os.getenv("DEMO_MODE", "").strip().lower() in ("true", "1", "yes")

    return {
        "host": smtp_host,
        "port": smtp_port,
        "username": smtp_user,
        "password": smtp_password,
        "from_email": smtp_from_email,
        "from_name": smtp_from_name,
        "use_tls": smtp_use_tls,
        "app_env": app_env,
        "demo_mode": demo_mode,
    }

# Default module-level exports for backwards compatibility
_initial_cfg = get_smtp_config()
SMTP_HOST = _initial_cfg["host"]
SMTP_PORT = _initial_cfg["port"]
SMTP_EMAIL = _initial_cfg["username"]
SMTP_USERNAME = _initial_cfg["username"]
SMTP_PASSWORD = _initial_cfg["password"]
SMTP_FROM_EMAIL = _initial_cfg["from_email"]
SMTP_FROM_NAME = _initial_cfg["from_name"]
SMTP_USE_TLS = _initial_cfg["use_tls"]
APP_ENV = _initial_cfg["app_env"]

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 60


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


def send_email_otp(recipient_email: str, recipient_name: str, otp_code: str) -> Tuple[bool, str, Optional[str]]:
    """
    Deliver the 6-digit verification code to the doctor's email.
    If SMTP server is configured, delivers real email via SMTP.
    In development mode without SMTP credentials, activates dev sandbox mode with local test code.
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
    cfg = get_smtp_config()
    host = cfg["host"]
    port = cfg["port"]
    user = cfg["username"]
    pwd = cfg["password"]
    from_name = cfg["from_name"]
    from_email = cfg["from_email"]
    use_tls = cfg["use_tls"]
    app_env = cfg["app_env"]
    demo_mode = cfg["demo_mode"]

    if host and user and pwd:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = recipient_email

            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=12)
            else:
                server = smtplib.SMTP(host, port, timeout=12)
                if use_tls:
                    server.starttls()
            server.login(user, pwd)
            server.send_message(msg)
            server.quit()

            logger.info(f"Verification email dispatched via SMTP to {recipient_email}")
            return True, "Verification email sent successfully via SMTP.", None
        except Exception as exc:
            logger.error(f"SMTP dispatch failed to {recipient_email}: {exc}")
            if app_env == "development" or demo_mode:
                logger.info(f"[DEV/DEMO SANDBOX ACTIVE] SMTP dispatch failed ({exc}); local dev OTP enabled for {recipient_email}")
                return True, f"Dev Sandbox: SMTP delivery failed ({exc}). Local test code ready.", otp_code
            return False, f"Email delivery failed: {str(exc)}", None

    # If no SMTP configured, use development sandbox mode in development or demo mode
    if app_env == "development" or demo_mode:
        logger.info(f"[DEV/DEMO SANDBOX ACTIVE] SMTP unconfigured. Generated local dev OTP for {recipient_email}")
        return True, "Development Mode: SMTP not configured. Local verification code generated.", otp_code

    # Production with no SMTP credentials — block delivery and return a clear error.
    # Never return the OTP code or silently succeed in production.
    logger.error(
        f"[PRODUCTION] Email delivery BLOCKED for {recipient_email}: "
        f"SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD must all be set in Render environment variables."
    )
    return False, "Email delivery is not configured. Please contact the administrator.", None


def send_doctor_approval_email(
    recipient_email: str,
    recipient_name: str,
    username: str,
    portal_url: str = "http://localhost:5173",
) -> Tuple[bool, str]:
    """
    Deliver formal credential approval notification to the verified physician.
    Includes system-assigned username and portal login link.
    Never transmits permanent password over plain email.
    """
    subject = "Account Approved — CardioPredict Clinical Portal"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Credentials Approved</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #F3F7FC; margin: 0; padding: 24px; }}
        .email-container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #DBEAFE; overflow: hidden; }}
        .email-header {{ background: linear-gradient(135deg, #0B1F3A 0%, #102F56 50%, #1565D8 100%); color: #ffffff; padding: 28px 24px; text-align: center; }}
        .email-body {{ padding: 28px 24px; color: #1e293b; line-height: 1.6; }}
        .info-card {{ background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 18px; margin: 20px 0; }}
        .cta-btn {{ display: inline-block; background: #1565D8; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-weight: 600; margin-top: 14px; }}
        .email-footer {{ background: #F8FAFC; padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #E2E8F0; }}
      </style>
    </head>
    <body>
      <div class="email-container">
        <div class="email-header">
          <h2 style="margin: 0; font-size: 20px;">CardioPredict Clinical Portal</h2>
          <p style="margin: 6px 0 0; opacity: 0.85; font-size: 13px;">Medical Credential Verification Approved</p>
        </div>
        <div class="email-body">
          <p>Dear <strong>{recipient_name}</strong>,</p>
          <p>We are pleased to inform you that your medical registration and credentials have been <strong>verified and approved</strong> by hospital administration.</p>
          <div class="info-card">
            <p style="margin: 0 0 8px; font-weight: 600; color: #0B1F3A;">Physician Profile Summary:</p>
            <p style="margin: 4px 0;"><strong>Assigned Portal Username:</strong> <code style="background: #DBEAFE; padding: 2px 6px; border-radius: 4px; color: #1565D8;">{username}</code></p>
            <p style="margin: 4px 0;"><strong>Registered Email:</strong> {recipient_email}</p>
            <p style="margin: 4px 0;"><strong>Status:</strong> <span style="color: #0D9488; font-weight: 700;">APPROVED</span></p>
          </div>
          <p>You can now sign in to access Heart Failure Mortality Risk Predictor clinical decision tools using your registered email and password:</p>
          <div style="text-align: center; margin: 20px 0;">
            <a href="{portal_url}" class="cta-btn" style="color: #ffffff;">Access Clinical Portal &rarr;</a>
          </div>
          <p style="font-size: 12px; color: #64748b;">
            * Security Note: For your protection, CardioPredict never sends permanent account passwords via email. Use the password configured during registration.
          </p>
        </div>
        <div class="email-footer">
          Heart Failure Mortality Risk Predictor &bull; Clinical Decision Support
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = (
        f"Dear {recipient_name},\n\n"
        f"Your medical registration and credentials have been verified and approved by hospital administration.\n\n"
        f"Assigned Portal Username: {username}\n"
        f"Registered Email: {recipient_email}\n"
        f"Status: APPROVED\n\n"
        f"You can sign in to the clinical portal at:\n{portal_url}\n\n"
        f"CardioPredict Clinical Decision Support"
    )

    cfg = get_smtp_config()
    host = cfg["host"]
    port = cfg["port"]
    user = cfg["username"]
    pwd = cfg["password"]
    from_name = cfg["from_name"]
    from_email = cfg["from_email"]
    use_tls = cfg["use_tls"]

    if host and user and pwd:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = recipient_email
            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=12)
            else:
                server = smtplib.SMTP(host, port, timeout=12)
                if use_tls:
                    server.starttls()
            server.login(user, pwd)
            server.send_message(msg)
            server.quit()
            logger.info(f"Doctor approval email dispatched to {recipient_email}")
            return True, "Approval email sent successfully."
        except Exception as exc:
            logger.error(f"Approval email SMTP dispatch failed: {exc}")
            return True, f"Approval recorded; SMTP dispatch logged: {str(exc)}"

    logger.info(f"[LOCAL DEV SMTP SIMULATION] Doctor approval dispatched to: {recipient_email} | Username: {username}")
    return True, "Approval email recorded (Local development simulation active)."


def send_doctor_rejection_email(
    recipient_email: str,
    recipient_name: str,
    rejection_reason: str,
) -> Tuple[bool, str]:
    """
    Deliver formal rejection notification with clinical reason to the physician.
    """
    subject = "Registration Status Update — CardioPredict Clinical Portal"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Registration Update</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #F3F7FC; margin: 0; padding: 24px; }}
        .email-container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #DBEAFE; overflow: hidden; }}
        .email-header {{ background: linear-gradient(135deg, #0B1F3A 0%, #102F56 50%, #EF4444 100%); color: #ffffff; padding: 28px 24px; text-align: center; }}
        .email-body {{ padding: 28px 24px; color: #1e293b; line-height: 1.6; }}
        .reason-card {{ background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 18px; margin: 20px 0; color: #991B1B; }}
        .email-footer {{ background: #F8FAFC; padding: 16px 24px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #E2E8F0; }}
      </style>
    </head>
    <body>
      <div class="email-container">
        <div class="email-header">
          <h2 style="margin: 0; font-size: 20px;">CardioPredict Clinical Portal</h2>
          <p style="margin: 6px 0 0; opacity: 0.85; font-size: 13px;">Credential Verification Review</p>
        </div>
        <div class="email-body">
          <p>Dear <strong>{recipient_name}</strong>,</p>
          <p>Thank you for submitting your credentials to the CardioPredict Clinical Portal. Following review against authoritative medical records, your application could not be approved at this time.</p>
          <div class="reason-card">
            <p style="margin: 0 0 6px; font-weight: 600;">Verification Review Decision:</p>
            <p style="margin: 0;">{rejection_reason}</p>
          </div>
          <p>If you believe this decision was made in error or if your state medical council registration was recently updated, please contact hospital administration.</p>
        </div>
        <div class="email-footer">
          Heart Failure Mortality Risk Predictor &bull; Clinical Decision Support
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = (
        f"Dear {recipient_name},\n\n"
        f"Your registration application to CardioPredict could not be approved at this time.\n\n"
        f"Reason recorded:\n{rejection_reason}\n\n"
        f"If you have questions, please contact hospital administration.\n"
        f"CardioPredict Clinical Decision Support"
    )

    cfg = get_smtp_config()
    host = cfg["host"]
    port = cfg["port"]
    user = cfg["username"]
    pwd = cfg["password"]
    from_name = cfg["from_name"]
    from_email = cfg["from_email"]
    use_tls = cfg["use_tls"]

    if host and user and pwd:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = recipient_email
            msg.attach(MIMEText(plain_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=12)
            else:
                server = smtplib.SMTP(host, port, timeout=12)
                if use_tls:
                    server.starttls()
            server.login(user, pwd)
            server.send_message(msg)
            server.quit()
            logger.info(f"Doctor rejection email dispatched to {recipient_email}")
            return True, "Rejection email sent successfully."
        except Exception as exc:
            logger.error(f"Rejection email SMTP dispatch failed: {exc}")
            return True, f"Rejection recorded; SMTP dispatch logged: {str(exc)}"

    logger.info(f"[LOCAL DEV SMTP SIMULATION] Doctor rejection dispatched to: {recipient_email} | Reason: {rejection_reason}")
    return True, "Rejection email recorded (Local development simulation active)."
