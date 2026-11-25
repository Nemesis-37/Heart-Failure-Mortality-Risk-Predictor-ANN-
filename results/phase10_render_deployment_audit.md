# Phase 10 — Render Cloud Deployment Audit

**Date:** 2026-11-25 14:29:27 UTC  
**Evaluation:** Render Infrastructure & Environment Audit (Task B.1)

---

## 1. Cloud Architecture Overview

The Heart Failure Mortality Risk Predictor is configured for single-service cloud deployment on Render:

- **Service Type:** Web Service (`web`)
- **Environment:** Python 3.11+
- **Build Command:** `./render-build.sh` (or `pip install -r requirements.txt && cd frontend && npm install && npm run build`)
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Database Dependency:** Managed PostgreSQL database (`heartmortality-db`)

---

## 2. Infrastructure Configuration (`render.yaml`)

```yaml
services:
  - type: web
    name: heart-failure-mortality-risk-predictor
    env: python
    plan: free
    buildCommand: bash render-build.sh
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: APP_ENV
        value: production
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: ADMIN_SECRET_KEY
        generateValue: true
      - key: ADMIN_EMAIL
        value: debashish.g333@gmail.com
      - key: ADMIN_PASSWORD
        value: admin_debashish123
      - key: ADMIN_USERNAME
        value: debashish.g333
      - key: ADMIN_FULL_NAME
        value: Hospital Administrator

```

---

## 3. Environment Variable Audit & Validation

| Variable Name | Render Configured Source | Local Development Value | Security & Purpose |
|---|---|---|---|
| `APP_ENV` | Explicit `production` | `development` | In production, strictly disables SQLite fallback and demo seeders. |
| `DATABASE_URL` | From `heartmortality-db` connectionString | Fallback SQLite / local PG | Connection string for PostgreSQL database engine. |
| `SECRET_KEY` | Render auto-generated secret | Loaded from `.env` | Secret key used for signing JWT access and session tokens. |
| `ALLOWED_ORIGINS`| `https://heart-failure-mortality-risk-predictor.onrender.com` | `localhost:5173, localhost:3000` | CORS whitelist restricting cross-origin browser requests. |
| `ADMIN_EMAIL` | Configured admin email | `debashish.g333@gmail.com` | Super administrator account for verification and oversight. |

---

## 4. Single-Service Static Asset Serving

In `main.py` lines 615–632:
- If `frontend/dist` exists, FastAPI mounts `/assets` using Starlette `StaticFiles`.
- A catch-all route `/{full_path:path}` serves `index.html` for client-side React routing, while ignoring API and auth endpoints.
- This eliminates the need for separate hosting of frontend and backend, reducing operational complexity and latency.
