# Phase 11.2 — Email Delivery & SMTP Configuration Audit Report

**Project:** Heart Failure Mortality Risk Predictor (CardioPredict Clinical Portal)  
**Audit Phase:** Phase 11.2 — SMTP Infrastructure and OTP Security Audit  
**Date:** November 26, 2026  
**Status:** **AUDITED & HARDENED (DELIVERY STATUS REPORTED AS BLOCKED DUE TO UNCONFIGURED SMTP)**

---

## 1. Executive Summary

This audit examined the end-to-end email dispatch pipeline for physician verification OTP codes in compliance with the Phase 11.2 strict delivery standards:
1. Generate cryptographically secure 6-digit OTPs using `secrets` CSPRNG.
2. Persist only PBKDF2-HMAC-SHA256 salted hashes; never store or log plain text.
3. 5-minute expiration window and maximum 5 verification attempts.
4. Cooldown rate-limiting between resends.
5. Provide clear errors when email delivery fails; report delivery as `BLOCKED` if SMTP is unconfigured; never simulate email delivery or log credentials/OTPs.

---

## 2. Environment Variables & SMTP Configuration Audit

### 2.1 Current Local Environment (`.env`)
```env
ADMIN_EMAIL=debashish.g333@gmail.com
ADMIN_RECOVERY_EMAIL=debashish.g333@gmail.com
DATABASE_URL=postgresql+psycopg2://postgres:hanuman@localhost:5433/heartmortality
```

### 2.2 Analysis of Required SMTP Parameters
| Environment Variable | Configured Value in Local `.env` | Required For Real Email Delivery | Audit Assessment |
| :--- | :--- | :--- | :--- |
| `SMTP_HOST` | *Not set* (empty string) | Yes (e.g., `smtp.gmail.com`, `smtp.sendgrid.net`) | **MISSING** |
| `SMTP_PORT` | *Not set* (defaults to 587) | Yes (587 for STARTTLS or 465 for SSL) | Default applied |
| `SMTP_USERNAME` | *Not set* (empty string) | Yes (authenticated sender address) | **MISSING** |
| `SMTP_PASSWORD` | *Not set* (empty string) | Yes (app password or API key) | **MISSING** |
| `SMTP_USE_TLS` | *Not set* (defaults to True) | Yes (STARTTLS encryption) | Default applied |
| `SMTP_FROM_EMAIL` | *Not set* (defaults to fallback) | Yes (verified sender domain) | Default applied |

### 2.3 Verdict on Email Delivery
Because `SMTP_HOST`, `SMTP_USERNAME`, and `SMTP_PASSWORD` are not configured in the developer's local environment, outbound email delivery is **BLOCKED**.

In strict adherence to Phase 11.2 rules, the system now:
- Returns `email_delivery_status: "BLOCKED"`.
- Explains: `"Email delivery is BLOCKED: SMTP credentials are not configured on the server."`
- Does NOT simulate success.
- Does NOT print the raw OTP in logs or console output.

---

## 3. Cryptographic OTP Implementation Audit

### 3.1 Token Generation
In `auth/email_service.py`:
```python
def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(6))
```
- **Entropy:** $10^6$ combinations (1,000,000 possible 6-digit combinations).
- **RNG Quality:** Uses Python's standard `secrets` library (cryptographically secure PRNG backed by OS CSPRNG `/dev/urandom` / `CryptGenRandom`).

### 3.2 Password/OTP Hashing
```python
def hash_otp(raw_otp: str) -> str:
    """Hash a 6-digit OTP with PBKDF2-HMAC-SHA256 and unique 16-byte salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", raw_otp.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"$otp$v=1${salt}${key.hex()}"
```
- Stored format: `$otp$v=1$<salt32hex>$<key64hex>`.
- Plaintext OTP is NEVER stored in database column `clinical.EmailOTP.otp_hash`.
- Verification uses `hmac.compare_digest` to prevent timing analysis side-channel attacks.

### 3.3 Security Lifecycle Parameters
- **Expiration:** 5 minutes (`expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)`).
- **Attempt Limit:** 5 attempts (`active_otp.attempts >= 5` invalidates code).
- **Cooldown:** 60 seconds (`OTP_COOLDOWN_SECONDS = 60`).
- **Single Use:** Set `is_used = True` upon verification; previous codes invalidated.

---

## 4. Production Deployment Recommendation (Render / Cloud)

To enable live email delivery in production or cloud deployment:
1. Configure environment variables in the Render Dashboard or `.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-clinical-portal@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   SMTP_FROM_EMAIL=no-reply@cardiopredict.org
   SMTP_FROM_NAME="CardioPredict Portal"
   SMTP_USE_TLS=yes
   ```
2. For Gmail, generate an **App Password** under Google Account Security (requires 2-Step Verification).
3. For SendGrid / AWS SES / Mailgun, use the SMTP API key as `SMTP_PASSWORD` and `apikey` or `smtp_user` as `SMTP_USERNAME`.

Once configured, `send_email_otp` will automatically detect credentials, perform the TLS handshake, dispatch the email, and return `email_delivery_status: "SENT"`.
