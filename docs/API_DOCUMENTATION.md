# Heart Failure Mortality Risk Predictor — Complete API Documentation

**Application Version:** 1.0.0  
**API Protocol:** RESTful over HTTP/1.1 & HTTP/2  
**Data Interchange Format:** JSON (`application/json`)  
**Base URLs:**
- Local Development: `http://localhost:8000`
- Render Production: `https://heart-failure-mortality-risk-predictor.onrender.com`

---

## 1. Architectural Overview & Clinical Notice

The Heart Failure Mortality Risk Predictor API provides secure, high-performance endpoints for clinical risk assessment and exploratory machine learning inference using the UCI Heart Failure Clinical Records dataset (299 patients, 11 baseline clinical features, excluding post-baseline follow-up duration).

> [!CAUTION]
> **EDUCATIONAL & RESEARCH PROTOTYPE DISCLAIMER**  
> This API is developed strictly for educational demonstration, academic research, and machine learning auditing. It has not received clearance or approval from the U.S. FDA, European EMA, or any national health regulatory authority. Outputs must never be used as diagnostic medical advice, clinical triage, or treatment selection.

---

## 2. Authentication & Authorization

Protected endpoints require a JSON Web Token (JWT) passed in the HTTP `Authorization` request header:
```http
Authorization: Bearer <access_token>
```

- **Algorithm:** HMAC-SHA256 (HS256)
- **Token Validity:** 12 hours from issuance
- **Identity Scoping (IDOR Prevention):** All clinical assessments, history, and dashboard metrics are automatically scoped to the authenticated physician's `doctor_id` extracted from the cryptographically verified token.

---

## 3. System & Database Health Endpoints

### 3.1. Basic Health Check
Returns runtime status and confirms whether machine learning artifacts are loaded in memory.

- **Route:** `GET /health`
- **Authentication:** None required
- **Response Status:** `200 OK`

```json
{
  "status": "healthy",
  "logistic_regression_loaded": true,
  "ann_loaded": true,
  "feature_count": 11
}
```

---

### 3.2. Database Health Diagnostics
Verifies active connection to the persistent storage layer. Accurately reports whether the database is running on PostgreSQL (cloud/local) or SQLite offline fallback.

- **Route:** `GET /db-health`
- **Authentication:** None required
- **Response Status:** `200 OK` (or `500 Internal Server Error` if disconnected)

```json
{
  "status": "connected",
  "database": "clinical_local.db",
  "dialect": "sqlite",
  "message": "Offline fallback SQLite database active (clinical_local.db)"
}
```

---

## 4. Physician Authentication & Registration Endpoints

### 4.1. Physician Login
Authenticates an approved physician or administrator. Enforces login rate limiting (max 5 consecutive failures before temporary cooldown).

- **Route:** `POST /auth/login`
- **Authentication:** None
- **Request Body:**

```json
{
  "email": "dr.carter@hospital.org",
  "password": "demo-doctor-2026"
}
```

- **Response Status:** `200 OK`

```json
{
  "role": "DOCTOR",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 43200,
  "doctor": {
    "doctor_id": "c1f8a84b-7f3e-4d5c-9c0d-1e2f3a4b5c6d",
    "full_name": "Dr. Julian Carter, MD",
    "email": "dr.carter@hospital.org",
    "mobile": "+1 (555) 019-2834",
    "medical_degree": "MD, FACC",
    "registration_number": "DEMO-CARTER-2026",
    "registration_council": "Medical Licensing Board",
    "verification_status": "APPROVED",
    "email_verified": true,
    "is_active": true
  }
}
```

- **Error Codes:**
  - `401 Unauthorized`: Invalid credentials or unapproved account.
  - `429 Too Many Requests`: Account temporarily locked due to excessive failed attempts.

---

### 4.2. Automated Client Registration
Allows new physicians to submit their credentials for administrative verification.

- **Route:** `POST /auth/register-json`
- **Authentication:** None
- **Request Body:**

```json
{
  "full_name": "Dr. Sarah Jenkins, MD",
  "email": "s.jenkins@general-hospital.org",
  "mobile": "+1 (555) 892-1144",
  "medical_degree": "MD (Cardiology)",
  "registration_number": "MED-REG-88291",
  "registration_council": "State Medical Council",
  "password": "SecurePassword2026!",
  "confirm_password": "SecurePassword2026!"
}
```

- **Response Status:** `201 Created`

```json
{
  "status": "success",
  "message": "Registration submitted successfully. Your credentials have been submitted for verification.",
  "doctor": {
    "doctor_id": "8f3b2190-...",
    "full_name": "Dr. Sarah Jenkins, MD",
    "email": "s.jenkins@general-hospital.org",
    "verification_status": "PENDING",
    "email_verified": false
  }
}
```

---

## 5. Machine Learning Inference Endpoints

Both prediction endpoints require an 11-feature patient payload.

### Patient Data Schema (`PatientData`)

| Field Name | Type | Range / Constraints | Description |
|---|---|---|---|
| `patient_reference_id` | `string` | Compulsory, non-empty | Clinical patient tracking ID (e.g. `PT-2026-001`) |
| `age` | `float` | $1.0 \le \text{age} \le 120.0$ | Chronological age in years |
| `anaemia` | `integer` | $0$ or $1$ | Reduction of haematocrit / red blood cells |
| `creatinine_phosphokinase` | `float` | $\ge 1.0$ | CPK blood enzyme level (mcg/L) |
| `diabetes` | `integer` | $0$ or $1$ | Diabetes mellitus diagnosis |
| `ejection_fraction` | `float` | $1.0 \le \text{EF} \le 100.0$ | Left ventricular ejection fraction (%) |
| `high_blood_pressure` | `integer` | $0$ or $1$ | Hypertension diagnosis |
| `platelets` | `float` | $\ge 1.0$ | Blood platelets count (kiloplatelets/mL) |
| `serum_creatinine` | `float` | $\ge 0.1$ | Serum creatinine concentration (mg/dL) |
| `serum_sodium` | `float` | $50.0 \le \text{sodium} \le 200.0$ | Serum sodium concentration (mEq/L) |
| `sex` | `integer` | $0$ (Female) or $1$ (Male) | Biological sex |
| `smoking` | `integer` | $0$ or $1$ | History of tobacco smoking |

---

### 5.1. Logistic Regression Inference
Computes mortality risk using the canonical scikit-learn Logistic Regression baseline model (12 parameters, AUROC 77.17%).

- **Route:** `POST /predict` (also aliased at `POST /api/predict`)
- **Authentication:** Optional for baseline testing; Bearer token recommended.
- **Request Body:**

```json
{
  "patient_reference_id": "PT-2026-001",
  "age": 65.0,
  "anaemia": 0,
  "creatinine_phosphokinase": 250.0,
  "diabetes": 0,
  "ejection_fraction": 35.0,
  "high_blood_pressure": 1,
  "platelets": 250000.0,
  "serum_creatinine": 1.3,
  "serum_sodium": 137.0,
  "sex": 1,
  "smoking": 0
}
```

- **Response Status:** `200 OK`

```json
{
  "model": "Logistic Regression",
  "patient_reference_id": "PT-2026-001",
  "predicted_class": 0,
  "predicted_label": "No death event predicted",
  "predicted_probability": 0.2854,
  "notice": "Educational prototype only; not for medical decisions."
}
```

---

### 5.2. Artificial Neural Network Inference
Computes mortality risk using the production PyTorch feedforward deep neural network ($11 \to 64 \to 32 \to 1$, 2,881 parameters).

- **Route:** `POST /predict-ann` (also aliased at `POST /api/predict-ann`)
- **Authentication:** Optional for baseline testing; Bearer token recommended.
- **Request Body:** Identical to `PatientData` schema above.
- **Response Status:** `200 OK`

```json
{
  "model": "Artificial Neural Network",
  "patient_reference_id": "PT-2026-001",
  "predicted_class": 0,
  "predicted_label": "No death event predicted",
  "predicted_probability": 0.1923,
  "notice": "Educational prototype only; not for medical decisions."
}
```

- **Error Codes:**
  - `422 Unprocessable Entity`: Input feature violates schema bounds (e.g., negative age, EF > 100, missing compulsory patient ID).

---

## 6. Patient Assessment & Clinical Records Endpoints

### 6.1. Create Patient Assessment
Records a complete patient clinical evaluation along with inference predictions in the database.

- **Route:** `POST /assessments`
- **Authentication:** Required (`Bearer <token>`)
- **Request Body:**

```json
{
  "patient_reference_id": "PT-2026-001",
  "age": 65.0,
  "anaemia": 0,
  "creatinine_phosphokinase": 250.0,
  "diabetes": 0,
  "ejection_fraction": 35.0,
  "high_blood_pressure": 1,
  "platelets": 250000.0,
  "serum_creatinine": 1.3,
  "serum_sodium": 137.0,
  "sex": 1,
  "smoking": 0,
  "selected_model": "Artificial Neural Network",
  "predicted_class": 0,
  "predicted_probability": 0.1923,
  "classification_threshold": 0.50
}
```

- **Response Status:** `200 OK` (or `201 Created`)

```json
{
  "assessment_id": "a92e10fc-8d3b-419b-a012-3c4d5e6f7a8b",
  "id": "a92e10fc-8d3b-419b-a012-3c4d5e6f7a8b",
  "doctor_id": "c1f8a84b-7f3e-4d5c-9c0d-1e2f3a4b5c6d",
  "patient_reference_id": "PT-2026-001",
  "assessment_code": "ASM-881920",
  "age": 65.0,
  "ejection_fraction": 35.0,
  "serum_creatinine": 1.3,
  "selected_model": "Artificial Neural Network",
  "predicted_class": 0,
  "predicted_probability": 0.1923,
  "created_at": "2026-11-25T14:30:00Z"
}
```

---

### 6.2. Physician Assessment History
Retrieves paginated historical evaluations performed by the authenticated physician.

- **Route:** `GET /history?page=1&limit=10&search=PT-2026`
- **Authentication:** Required (`Bearer <token>`)
- **Response Status:** `200 OK`

```json
{
  "items": [
    {
      "assessment_id": "a92e10fc-...",
      "patient_reference_id": "PT-2026-001",
      "age": 65.0,
      "ejection_fraction": 35.0,
      "serum_creatinine": 1.3,
      "selected_model": "Artificial Neural Network",
      "predicted_class": 0,
      "predicted_probability": 0.1923,
      "created_at": "2026-11-25T14:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 10
}
```

---

### 6.3. Clinical Dashboard Analytics Summary
Aggregates assessment metrics, model usage breakdown, and risk stratification distributions for the logged-in doctor.

- **Route:** `GET /dashboard/summary`
- **Authentication:** Required (`Bearer <token>`)
- **Response Status:** `200 OK`

```json
{
  "total_assessments": 14,
  "total_high_risk": 4,
  "total_moderate_risk": 5,
  "total_low_risk": 5,
  "ann_usage_count": 9,
  "logistic_regression_usage_count": 5,
  "recent_assessments": [...]
}
```

---

## 7. Standard HTTP Status Code Reference

| Status Code | Meaning | Typical Trigger |
|---|---|---|
| `200 OK` | Request succeeded | Successful query or prediction |
| `201 Created` | Resource created | Successful registration or assessment creation |
| `400 Bad Request` | Malformed request | Password mismatch or missing compulsory fields |
| `401 Unauthorized` | Authentication failure | Missing, invalid, or expired JWT token |
| `403 Forbidden` | Access denied | Physician account not approved or disabled |
| `404 Not Found` | Resource not found | Assessment does not exist or belongs to another physician (IDOR) |
| `422 Unprocessable Entity`| Schema violation | Feature value out of physiological range (e.g. `age < 1`) |
| `429 Too Many Requests` | Rate limit triggered | More than 5 failed login attempts in succession |
| `500 Internal Error` | Server runtime fault | Unhandled database connection failure |
