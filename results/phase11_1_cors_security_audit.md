# Phase 11.1 — CORS Security & Hardening Audit

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 11.1 — Connectivity, CORS, Test Count & Visualizer Safety Audit  
**Date:** November 2026  
**Component Audited:** `backend/main.py` (`CORSMiddleware` configuration)  
**Verification Results:** 5 / 5 Preflight Scenarios Verified (Status 200 for Trusted, Status 400 for Untrusted)  

---

## 1. Vulnerability Analysis: Overly Permissive Regex

### Previous Configuration (Phase 11 Initial State)
In the initial Phase 11 implementation, `main.py` contained:
```python
cors_origin_regex = r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.onrender\.com)$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Security Defect
The regular expression `https://.*\.onrender\.com` matched **any subdomain on Render**, including third-party applications deployed by arbitrary users on the Render platform (e.g. `https://malicious-app-xyz.onrender.com`).  
Because `allow_credentials=True` was enabled, a malicious site hosted on Render could execute cross-origin authenticated requests if a user had an active clinical session.

---

## 2. Hardened Architecture (Phase 11.1 Implementation)

The broad regex was decommissioned and replaced by an **explicit trusted-origin allowlist** that strictly differentiates production from development:

```python
is_prod_env = os.getenv("APP_ENV", "development").lower() == "production" or bool(os.getenv("RENDER"))
raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")

# Explicit canonical production domain
TRUSTED_PROD_ORIGIN = "https://heart-failure-mortality-risk-predictor.onrender.com"

# Build hardened origin allowlist
if is_prod_env:
    # In production: strictly allow configured trusted production origins only; do NOT allow localhost or arbitrary *.onrender.com subdomains
    prod_origins = [TRUSTED_PROD_ORIGIN]
    if frontend_url:
        prod_origins.append(frontend_url)
    if raw_origins:
        prod_origins.extend([o.strip().rstrip("/") for o in raw_origins.split(",") if o.strip()])
    allowed_origins = list(dict.fromkeys(prod_origins))
    cors_origin_regex = None  # No wildcard regex in production; strictly adhere to trusted allowlist
else:
    # In development: allow local developer loopback ports and trusted test origins
    dev_origins = [
        TRUSTED_PROD_ORIGIN,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    if frontend_url:
        dev_origins.append(frontend_url)
    if raw_origins:
        dev_origins.extend([o.strip().rstrip("/") for o in raw_origins.split(",") if o.strip()])
    allowed_origins = list(dict.fromkeys(dev_origins))
    # In dev, regex is restricted to localhost / 127.0.0.1 on any port only
    cors_origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
)
```

---

## 3. Security Requirements Compliance Matrix

| Requirement | Implementation Mechanism | Audit Result |
| :--- | :--- | :---: |
| **No Arbitrary Production Origins** | Removed wildcard `https://.*\.onrender\.com`; `cors_origin_regex = None` in production. | **COMPLIANT** |
| **Explicit Trusted Allowlist** | Locked to `https://heart-failure-mortality-risk-predictor.onrender.com` plus explicit `ALLOWED_ORIGINS` / `FRONTEND_URL`. | **COMPLIANT** |
| **Localhost for Development Only** | In production (`is_prod_env=True`), `http://localhost:*` and `http://127.0.0.1:*` are excluded. In development, developer loopback ports are permitted. | **COMPLIANT** |
| **Preserve Auth & Registration** | `OPTIONS /auth/register` preflight returns 200 with credentials for trusted origins. | **COMPLIANT** |
| **Reject Untrusted Preflights** | Origins not matching the allowlist trigger Starlette 400 rejection with `access-control-allow-origin` withheld. | **COMPLIANT** |
| **Restricted Headers & Methods** | Replaced wildcard `["*"]` with explicit HTTP verbs and necessary clinical authentication headers (`Authorization`, `Content-Type`, etc.). | **COMPLIANT** |

---

## 4. Preflight Test Scenarios & Automated Verification

The test harness `scripts/verify_phase11.py` executes 5 automated preflight requests against `/predict`:

```
--- 5. CORS Configuration Verification ---
[PASS] CORS Preflight from https://heart-failure-mortality-risk-predictor.onrender.com - status=200, allowed=True, expected=True
[PASS] CORS Preflight from https://preview-branch-123.onrender.com - status=400, allowed=False, expected=False
[PASS] CORS Preflight from http://localhost:5173 - status=200, allowed=True, expected=True
[PASS] CORS Preflight from http://127.0.0.1:5173 - status=200, allowed=True, expected=True
[PASS] CORS Preflight from https://unauthorized-malicious-domain.com - status=400, allowed=False, expected=False
```

1. **Canonical Production Domain:** `status 200`, `access-control-allow-origin: https://heart-failure-mortality-risk-predictor.onrender.com`, `access-control-allow-credentials: true` &rarr; **PASSED**.
2. **Arbitrary Render Subdomain (`preview-branch-123.onrender.com`):** `status 400 Disallowed CORS origin` &rarr; **PASSED (Blocked)**.
3. **Local Dev (`localhost:5173`):** `status 200`, allowed &rarr; **PASSED**.
4. **Local Loopback (`127.0.0.1:5173`):** `status 200`, allowed &rarr; **PASSED**.
5. **Untrusted External Domain:** `status 400 Disallowed CORS origin` &rarr; **PASSED (Blocked)**.
