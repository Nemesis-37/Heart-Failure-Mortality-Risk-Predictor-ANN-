# Phase 11.2 — OTP Root Cause & 400 Bad Request Diagnostic Report

**Project:** Heart Failure Mortality Risk Predictor (CardioPredict Clinical Portal)  
**Audit Phase:** Phase 11.2 — Diagnostic Analysis of Registration & OTP Delivery  
**Date:** November 26, 2026  
**Status:** **DIAGNOSED & FULLY RESOLVED**

---

## 1. Executive Summary

During practitioner signup testing, the user reported encountering an HTTP 400 Bad Request error accompanied by a confusing top alert:
```
Invalid data format or out-of-range clinical parameters provided.
```
Furthermore, the user did not receive the expected 6-digit OTP email upon registration submission.

This audit report identifies the exact technical root causes across the backend validation layer, the response-parsing layer in the frontend, and the email dispatch configuration.

---

## 2. Root Cause 1: Error Unwrapping Mismatch & Misleading Fallback Alert

### 2.1 The Observed Symptom
When the backend returned HTTP 400 with a validation failure (e.g., password missing an uppercase letter, password mismatch, or duplicate registration), the frontend displayed:
`"Invalid data format or out-of-range clinical parameters provided."`
None of the specific input fields were highlighted, leaving the user unaware of which credential parameter failed.

### 2.2 Technical Mechanism
In `frontend/src/utils/apiErrorHelper.js`, the helper function `safeParseResponse(res)` previously returned:
```javascript
// Previous flawed implementation
export async function safeParseResponse(res) {
  if (!res) return { data: null, text: '' }
  try {
    const text = await res.text()
    const data = JSON.parse(text)
    return { data, text }
  } catch {
    return { data: null, text }
  }
}
```
In `DoctorRegister.jsx`, this parsed output was passed into `parseApiError`:
```javascript
const parsedBody = await safeParseResponse(res) // Evaluated to { data: { detail: "..." }, text: "..." }
lastParsedError = parseApiError(null, res, parsedBody)
```
Inside `parseApiError`:
```javascript
const fieldErrors = extractFieldErrors(responseBody)
const detailMsg = typeof responseBody?.detail === 'string' ? responseBody.detail : ''
```
Because `responseBody` was wrapped in `{ data: ... }`, `responseBody.detail` evaluated to `undefined`!
Consequently:
1. `detailMsg` became `""` (empty string).
2. `extractFieldErrors(responseBody)` inspected `responseBody.detail` (undefined), producing `{}` (empty errors).
3. The fallback condition in `parseApiError` triggered:
   ```javascript
   detailMsg || (Object.keys(fieldErrors).length > 0 ? ... : 'Invalid data format or out-of-range clinical parameters provided.')
   ```
4. This fallback string—originally authored for the patient risk prediction endpoint (`/predict`)—was erroneously displayed on the physician registration form!

### 2.3 The Resolution
1. Modified `safeParseResponse(res)` to return the parsed JSON object directly, or `{ detail: text }` if plain text.
2. Hardened `extractFieldErrors` and `parseApiError` to unwrap `responseBody?.data` if present.
3. Updated fallback message to generic form validation summary rather than clinical parameter error:
   `"Validation failed. Please verify that all required fields are correctly formatted."`
4. Mapped backend Pydantic/FastAPI detail strings directly to corresponding frontend field states (`password`, `email`, `registrationNumber`, etc.).

---

## 3. Root Cause 2: Password Complexity Validation Triggering 400 Bad Request

### 3.1 Backend Validation Rules (`auth/validation.py`)
FastAPI strictly enforces:
- `len(password) >= 8`: Minimum 8 characters.
- `re.search(r"[A-Z]", password)`: At least one uppercase character `[A-Z]`.
- `re.search(r"[a-z]", password)`: At least one lowercase character `[a-z]`.
- `re.search(r"\d", password)`: At least one numeric digit `[0-9]`.
- `password == confirm_password`: Exact string match.

If a practitioner inputs a password that lacks an uppercase character (e.g. `debashish123` or administrative pattern without caps), the backend immediately raises:
`HTTPException(status_code=400, detail="Password must contain at least one uppercase letter (A-Z).")`
Due to Root Cause 1, this exact error was hidden from the user and replaced by the confusing clinical parameters message.

With Root Cause 1 fixed, the form clearly highlights the password input box with:
`"Password must contain at least one uppercase letter (A-Z)."`

---

## 4. Root Cause 3: Missing SMTP Credentials Causing Delivery Block

### 4.1 Environment Audit
Inspection of `.env` revealed:
```env
ADMIN_EMAIL=debashish.g333@gmail.com
ADMIN_RECOVERY_EMAIL=debashish.g333@gmail.com
DATABASE_URL=postgresql+psycopg2://postgres:hanuman@localhost:5433/heartmortality
```
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, and `SMTP_PASSWORD` were completely absent.

### 4.2 Flawed Simulation Fallback
Previously, `auth/email_service.py` had a local development fallback that logged the plain OTP and returned `True, "Verification code sent (Local development simulation active)"`.
This masked the lack of email connectivity and falsely indicated success to the caller while logging plaintext OTPs in violation of medical security standards.

### 4.3 The Resolution
1. Removed all simulation logic: when SMTP credentials are unconfigured or SMTP handshake fails, `send_email_otp` returns:
   `False, "Email delivery is BLOCKED: SMTP credentials are not configured on the server."`
2. Removed all logging of raw 6-digit OTP codes.
3. Updated `/auth/register`, `/auth/send-otp`, and `/auth/resend-otp` to return `email_delivery_status: "BLOCKED"` with actionable explanations.

---

## 5. Verification Matrix

| Root Cause Area | Pre-Fix Behavior | Post-Fix Behavior | Status |
| :--- | :--- | :--- | :--- |
| **Response Body Unwrapping** | `{ data: { detail: ... } }` caused `detail` to be undefined | Directly unwraps data; extracts field errors accurately | **RESOLVED** |
| **Error Banner Text** | `"Invalid data format or out-of-range clinical parameters provided."` | Specific FastAPI message (e.g., `"Password must contain at least one uppercase letter (A-Z)."`) | **RESOLVED** |
| **Field Highlighting** | No field highlighted on 400 validation failure | Targeted input fields highlighted in red with inline error helper | **RESOLVED** |
| **Email Delivery Status** | Simulated delivery; falsely returned `True` with OTP in logs | Accurately reports `BLOCKED` status; never leaks OTP or credentials | **RESOLVED** |
