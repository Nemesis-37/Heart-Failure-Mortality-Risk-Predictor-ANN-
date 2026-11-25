# Phase 11.1 — Production API Routing & Architecture Audit

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 11.1 — Connectivity, CORS, Test Count & Visualizer Safety Audit  
**Date:** November 2026  
**Files Audited:**
- `render.yaml`
- `render-build.sh`
- `frontend/vite.config.js`
- `frontend/src/apiConfig.js`
- `backend/main.py`

---

## 1. Objective

Determine whether relative URLs such as `/predict` actually reach FastAPI in the deployed Render architecture, clarify the role of reverse proxies in development vs. production, and establish strict safeguards ensuring that `localhost` is never contacted in a deployed environment.

---

## 2. Render Deployment Architecture Analysis

### 2.1 The Render Configuration (`render.yaml`)
Inspection of `render.yaml` reveals the complete production topology:

```yaml
services:
  - type: web
    name: heart-failure-mortality-risk-predictor
    env: python
    plan: free
    buildCommand: bash render-build.sh
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Key Architectural Insight:**  
The application is deployed on Render as a **single unified web service** running Python (`uvicorn main:app`), **NOT** as two separate decoupled services (i.e. not a separate static site plus backend web service).

### 2.2 The Build Pipeline (`render-build.sh`)
During deployment, Render executes `render-build.sh`:
1. `npm --prefix frontend install` installs React, Vite, and Tailwind dependencies.
2. `npm --prefix frontend run build` compiles the React frontend into static bundles in `frontend/dist/`.
3. `python -m pip install -r requirements.txt` installs FastAPI, PyTorch, scikit-learn, and Uvicorn.

### 2.3 The Host Mounting Mechanism (`backend/main.py`)
In `backend/main.py` (lines 618–635):
```python
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith(("api", "auth", "admin", "docs", "openapi.json", "health", "predict", "db-health")):
            raise HTTPException(status_code=404, detail="Not Found")
        target_file = FRONTEND_DIST / full_path
        if target_file.is_file():
            return FileResponse(str(target_file))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
```

---

## 3. How Relative URLs Function in Production vs. Development

| Feature / Behavior | Development Environment (Local) | Unified Production Deployment (Render) | Isolated Static Site Deployment (Decoupled) |
| :--- | :--- | :--- | :--- |
| **Hosting Topology** | Vite dev server (port 5173) + Uvicorn backend (port 8000) | Single Uvicorn process serving API and static assets from `frontend/dist` | Vite build on Render Static Site; Backend on separate Web Service |
| **Origin (`window.location.origin`)** | `http://localhost:5173` | `https://heart-failure-mortality-risk-predictor.onrender.com` | `https://custom-frontend.onrender.com` |
| **Reverse Proxy Role** | `vite.config.js` `server.proxy` forwards `/api`, `/predict`, `/auth` to `127.0.0.1:8000` | **No reverse proxy needed:** FastAPI handles both API routes and static asset serving on the identical port/origin. | Requires Render rewrite rule or explicit `VITE_API_URL` environment variable. |
| **Relative URL `/predict` Resolution** | Forwards via Vite proxy to `http://127.0.0.1:8000/predict` | Directly calls `https://...onrender.com/predict`, which triggers `@app.post("/predict")` | **Fails with 404** unless `VITE_API_URL` is set or reverse proxy is configured. |
| **Localhost Fallbacks** | Permitted (`http://127.0.0.1:8000`) if Vite proxy drops | **Strictly Disallowed:** Discarded by `apiConfig.js` guard | **Strictly Disallowed:** Discarded by `apiConfig.js` guard |

### Confirmation of Relative URL Routing
In the deployed Render architecture specified by `render.yaml`:
- When a user visits `https://heart-failure-mortality-risk-predictor.onrender.com`, FastAPI serves `frontend/dist/index.html`.
- A browser request targeting relative path `/predict` resolves to `https://heart-failure-mortality-risk-predictor.onrender.com/predict`.
- FastAPI route table matches `@app.post("/predict")` before the fallback `serve_frontend` wildcard.
- **Result:** Relative URLs `/predict`, `/predict-ann`, `/health`, `/auth/register` genuinely reach FastAPI directly in this architecture.

---

## 4. Environment-Aware URL Resolution Safeguards

To prevent configuration errors (e.g. baking `VITE_API_URL=http://localhost:8000` into production builds), `frontend/src/apiConfig.js` enforces strict safety invariants:

1. **Host-Aware Inspection:**
   ```javascript
   const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0' || hostname === '::1';
   ```
2. **Localhost Discard on Public Domains:**
   If `!isLocalhost` and `envUrl` contains `localhost` or `127.0.0.1`, `resolveApiBaseUrl()` discards the environment variable and falls back to relative paths (`""`), ensuring client browsers never try connecting to `127.0.0.1`.
3. **Loopback Candidate Protection:**
   In `getPredictionCandidateUrls()`, `getAuthCandidateUrls()`, and `getHealthCandidateUrls()`, loopback URLs (`http://127.0.0.1:8000/...`) are ONLY appended when `isLocalhost === true`. In production browsers, candidate lists contain only relative paths or valid public URLs.

---

## 5. Verification Status: Local vs. Cloud

- **Locally Tested:**
  - ASGI request routing to `/predict`, `/api/predict`, `/predict-ann`, `/api/predict-ann`: **VERIFIED (200 OK)**.
  - Health checks `/health`, `/api/health`, `/db-health`, `/api/db-health`: **VERIFIED (200 OK)**.
  - Registration `/auth/register`, `/api/auth/register`: **VERIFIED (201 Created)**.
  - Static file mounting and SPA index fallback: **VERIFIED**.
- **Cloud Tested (Live Render Service):**
  - Live HTTP requests over the public internet to Render servers: **NOT TESTED** (restricted by execution sandbox network boundary).
  - Must be confirmed post-deployment via Render Dashboard logs and browser Network tab.
