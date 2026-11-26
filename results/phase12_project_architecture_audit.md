# Phase 12 — Complete Project Architecture & Dependency Map Audit

**Project:** Heart Failure Mortality Risk Predictor (CardioPredict Clinical Portal)  
**Execution Date:** November 26, 2026  
**Auditor:** Antigravity Autonomous Engineering Agent  
**Status:** COMPLETE — ARCHITECTURE MAPPED

---

## 1. High-Level Architecture Overview

CardioPredict is an enterprise clinical decision support and heart failure mortality risk prediction portal utilizing a dual-engine architecture:
1. **Frontend:** React 19 Single Page Application (SPA) built with Vite 6 and Tailwind CSS v4, supporting strict dark-mode clinical UI, live SVG ECG telemetry visualizations, and comprehensive state persistence across browser sessions.
2. **Backend:** FastAPI (Python 3.11/3.13) high-performance REST API with unified asynchronous routing, CORS hardening, rate-limited email OTP verification, and dual-tier authentication (physicians and hospital administrators).
3. **Database Layer:** Hybrid PostgreSQL (primary for production on Render) and SQLite (automatic offline local developer fallback), managed through SQLAlchemy 2.0 ORM with Alembic schema migration support under the `clinical` schema.
4. **Machine Learning Engines:** 
   - **Logistic Regression Pipeline:** Scikit-learn calibrated pipeline combining `StandardScaler` with positive-class probability extraction across 11 clinical features.
   - **Artificial Neural Network (ANN):** PyTorch feed-forward deep neural network (11 $\to$ 64 $\to$ 32 $\to$ 1 with 2,881 parameter elements), ReLU activations, Dropout, and Sigmoid terminal layer evaluated under `torch.inference_mode()`.

```
[ Clinical User / Physician / Admin ]
                 │
                 ▼
  [ React 19 Frontend SPA (Vite 6) ]
  (Static Site: heart-failure-mortality-risk-predictor.onrender.com)
                 │
                 │ REST / JSON (getAuthCandidateUrls / getPredictionCandidateUrls)
                 ▼
  [ FastAPI Application (main.py) ]
  (Web Service: heart-failure-mortality-risk-predictor-mfet.onrender.com)
        │                 │                  │
        ▼                 ▼                  ▼
 [ Auth Router ]   [ Admin Router ]   [ ML Diagnostic Engines ]
  - Argon2id/PBKDF2 - Doctor Approval  - Logistic Regression Pipeline
  - Email OTP       - Audit History    - PyTorch ANN (11->64->32->1)
  - JWT Tokens      - Stats / Pending  - Model Metrics & Diagnostics
        │                 │                  │
        └─────────────────┼──────────────────┘
                          │
                          ▼
            [ SQLAlchemy 2.0 ORM ]
            (database/models.py)
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
   [ PostgreSQL (Production) ]   [ SQLite (Local Fallback) ]
   - Schema: clinical            - clinical_local.db
```

---

## 2. Frontend Architecture & Component Map

### A. Routing & View Hierarchy (`App.jsx`)
The frontend uses state-driven view routing (`authMode` and `activePage`) with full session restoration:
- **Public Views (`!doctorUser`):**
  - `login` $\to$ `UnifiedLogin.jsx`: Multi-role physician and hospital administrator login portal.
  - `register` $\to$ `DoctorRegister.jsx`: Two-column clinical credential onboarding portal with document proof upload and live ECG telemetry visualizer.
  - `otp` $\to$ `DoctorOtpVerification.jsx`: 6-digit cryptographic verification portal with 5-minute expiry, 60s cooldown timer, and animated waiting telemetry.
  - `admin` $\to$ `AdminDashboard.jsx`: Hospital administration dashboard for doctor credential approvals and system audit.
- **Physician Authenticated Views (`doctorUser`):**
  - `AppLayout.jsx`: Master navigation shell with top navigation bar, status indicators, and profile modal.
  - `dashboard` $\to$ `DashboardHome.jsx`: Summary metrics, quick action tiles, and patient summary charts.
  - `prediction` $\to$ `DoctorDashboard.jsx`: Dual-engine risk evaluation workspace with sliders, quick presets, and live comparative risk graphs.
  - `assessments` $\to$ `PatientAssessmentsPage.jsx`: Clinical assessment tracking with triage badges.
  - `history` $\to$ `PredictionHistoryPage.jsx`: Filterable, searchable diagnostic prediction log.
  - `clinical-guide` $\to$ `ClinicalGuidePage.jsx`: Clinical decision-support handbook.
  - `counselling` $\to$ `HeartHealthCounsellingPage.jsx`: Patient counselling card generator with downloadable PDF report (`generateCounsellingPdf.js`).

### B. API URL Resolution (`apiConfig.js`)
* **Production Resolution:** Automatically resolves to `https://heart-failure-mortality-risk-predictor-mfet.onrender.com` when running on `*.onrender.com` without requiring environment variables.
* **Development Resolution:** Dispatches through Vite proxy to `http://127.0.0.1:8000` with direct fallback candidates (`http://127.0.0.1:8000` and `http://localhost:8000`).

---

## 3. Backend Architecture & Route Inventory

FastAPI registers 106 total routes across root and prefix routers:

### A. System & Health Endpoints
- `GET /`, `GET /health`, `GET /api/health`: Comprehensive system health, model readiness, and feature counts.
- `GET /db-health`, `GET /api/db-health`: PostgreSQL dialect verification and schema connectivity check.
- `GET /openapi.json`, `GET /docs`, `GET /redoc`: Interactive OpenAPI documentation.

### B. Machine Learning Diagnostic Endpoints
- `POST /predict`, `POST /api/predict`: Scikit-learn Logistic Regression inference.
- `POST /predict-ann`, `POST /api/predict-ann`: PyTorch Artificial Neural Network inference.
- `GET /metrics`, `GET /api/metrics`: Frozen research model evaluation metrics and confusion matrices.

### C. Authentication Router (`/auth` prefix)
- `POST /auth/login`, `POST /api/auth/login`: Unified physician and administrator authentication.
- `POST /auth/register`, `POST /api/auth/register`: Multipart form data physician registration with document upload.
- `POST /auth/register-json`: Programmatic JSON registration for automated clients.
- `POST /auth/send-otp`, `POST /auth/resend-otp`: Cryptographic 6-digit OTP generation and email dispatch.
- `POST /auth/verify-otp`, `POST /api/auth/verify-otp`: Verification of salted PBKDF2 hash.
- `GET /auth/me`, `POST /auth/logout`, `POST /auth/refresh`: Session token management.
- `POST /auth/upload-profile-photo`, `GET /auth/profile-photo/{doctor_id}`: Physician profile photo service.

### D. Administration Router (`/admin` prefix)
- `POST /admin/login`: Direct administrator credentials verification.
- `GET /admin/doctors/pending`: Queue of physicians who verified email and await council review.
- `GET /admin/doctors`: Complete directory of registered physicians.
- `PATCH /admin/doctors/{doctor_id}/approve`: Medical council approval transition (`PENDING` $\to$ `APPROVED`).
- `PATCH /admin/doctors/{doctor_id}/reject`: Application rejection with clinical audit reason.
- `GET /admin/system-stats`: Hospital portal telemetry and activity summaries.

### E. Patient Assessments Router (`/assessments` and `/dashboard` prefixes)
- `GET /assessments`, `POST /assessments`, `DELETE /assessments/{id}`: Patient risk cohort management.
- `GET /dashboard/summary`: High-level aggregated mortality risk indicators.

---

## 4. Database Schema & Persistence Models

Managed through SQLAlchemy 2.0 under PostgreSQL schema `clinical` with fallback to local SQLite:

| Model Class | Table Name | Primary Key | Key Foreign Keys & Indexes |
|:---|:---|:---|:---|
| `Doctor` | `clinical.Doctors` | `doctor_id` (UUID) | Unique on `email`, `registration_number` |
| `DoctorSession` | `clinical.DoctorSessions` | `session_id` (UUID) | FK `doctor_id`, indexed `refresh_token_hash` |
| `EmailOTP` | `clinical.EmailOTP` | `otp_id` (UUID) | FK `doctor_id`, indexed `expires_at`, `created_at` |
| `Administrator`| `clinical.Administrators` | `admin_id` (UUID) | Unique on `username`, `email` |
| `Assessment` | `clinical.Assessments` | `assessment_id` (UUID)| Unique on `assessment_number` |
| `Prediction` | `clinical.Predictions` | `prediction_id` (UUID)| FK `assessment_id`, indexed `created_at` |

---

## 5. Machine Learning Frozen Artifacts Audit

- **Logistic Regression Pipeline:** `models/logistic_regression_pipeline.joblib`
  - Steps: `[('scaler', StandardScaler()), ('classifier', LogisticRegression())]`
  - Calibrated positive class mortality probability output.
  - Frozen parameters: Zero modification permitted.
- **Artificial Neural Network Checkpoint:** `models/ann_model.pth`
  - Architecture: `11 -> 64 -> 32 -> 1`
  - Total Parameter Elements: **2,881**
    - `network.0.weight`: (64, 11) = 704
    - `network.0.bias`: (64,) = 64
    - `network.3.weight`: (32, 64) = 2,048
    - `network.3.bias`: (32,) = 32
    - `network.6.weight`: (1, 32) = 32
    - `network.6.bias`: (1,) = 1
  - Features: 11 standardized clinical biomarkers (Age, Anaemia, Creatinine Phosphokinase, Diabetes, Ejection Fraction, High Blood Pressure, Platelets, Serum Creatinine, Serum Sodium, Sex, Smoking).
  - Scaler: `models/ann_scaler.joblib` (`n_features_in_ = 11`).

---

## 6. Pre-Execution Defects & Discrepancies Identified

1. **`argon2-cffi` Python Module Discrepancy:**
   - In `auth/security.py`, `from argon2 import PasswordHasher` is trapped with fallback to PBKDF2-SHA256 (600,000 iterations). While secure, native Argon2id should be available if binary wheels match.
2. **Scikit-Learn Version Compatibility:**
   - Local environment has `scikit-learn==1.9.1`, while `requirements.txt` specifies `>=1.6.1`. Both load artifacts cleanly with zero deserialization warnings.
3. **Database Port Fallback Behavior:**
   - When PostgreSQL is unavailable locally (port 5433 offline), the system gracefully switches to offline SQLite (`clinical_local.db`). In production, this fallback is disabled to guarantee PostgreSQL persistence.
