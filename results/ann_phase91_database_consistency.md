# Phase 9.1 — Database Consistency & Environment Audit Report

**Project:** Heart Failure Mortality Risk Predictor  
**Phase:** 9.1 — Final Deployment Consistency Audit  
**Date:** November 2026  
**Scope:** Investigation of active database dialect, local socket connectivity, and deployment configuration.  

---

## 1. Executive Summary

During Phase 9 verification, the database diagnostic endpoint (`/db-health`) reported connectivity using **SQLite (`clinical_local.db`)** rather than PostgreSQL, despite the presence of a PostgreSQL connection string in `.env`.

This audit investigated the database connection selection logic, inspected local network sockets, and verified the production database enforcement safeguards.

> [!IMPORTANT]
> **Key Database Findings:**
> 1. **Active Local Engine:** The local application is currently executing on **SQLite (`clinical_local.db`)**, not PostgreSQL.
> 2. **Root Cause:** In `.env`, `DATABASE_URL` specifies `postgresql+psycopg2://postgres:***@localhost:5433/heartmortality`. However, the local PostgreSQL service on port 5433 is **closed / offline** on this machine.
> 3. **Fast Fallback Protection:** To prevent the application from hanging for 2 minutes on Windows during TCP connection attempts when PostgreSQL is offline, `backend/database/config.py` performs a 0.5-second socket probe. When the port is unreachable and `ALLOW_SQLITE_OFFLINE=true` in development mode, it cleanly switches to `clinical_local.db`.
> 4. **Testing Status Classification:**
>    - **Local SQLite Testing:** ✅ **PASSED** (100% of tables, CRUD operations, and relations verified).
>    - **Local PostgreSQL Testing:** ⚠️ **BLOCKED / NOT TESTED** (Local service offline on port 5433).
>    - **Render / Deployed PostgreSQL:** ⚠️ **BLOCKED / NOT TESTED** (Pending cloud deployment).

---

## 2. Configuration & Connection Logic Inspection

### 2.1 Environment Variable Configuration (`.env`)
```bash
ADMIN_EMAIL=debashish.g333@gmail.com
ADMIN_RECOVERY_EMAIL=debashish.g333@gmail.com
DATABASE_URL=postgresql+psycopg2://postgres:********@localhost:5433/heartmortality
ALLOW_SQLITE_OFFLINE=true
APP_ENV=development
```

### 2.2 Connection Resolution in `backend/database/config.py`
In lines 98–160 of `backend/database/config.py`:
1. `_is_pg_port_reachable(pg_url, timeout_sec=0.5)` tests whether a TCP connection can be established to the host and port specified in `_pg_url`.
2. Socket probes conducted during Phase 9.1 audit:
   - `localhost:5432`: **Closed**
   - `localhost:5433`: **Closed**
3. Because `not is_prod and not _is_pg_port_reachable(_pg_url)` evaluated to `True`, the backend logged:
   `"PostgreSQL server is unreachable on local port; immediately switching to offline SQLite fallback."`
4. The backend then initialized the SQLite engine (`clinical_local.db`) with Write-Ahead Logging (WAL) mode enabled.

---

## 3. Production PostgreSQL Enforcement Fence

We audited lines 156–159 of `backend/database/config.py` to ensure that SQLite cannot silently slip into production:

```python
if engine is None:
    if is_prod:
        raise RuntimeError(
            "FATAL: Production requires PostgreSQL DATABASE_URL. "
            "SQLite/MSSQL are strictly forbidden in production."
        )
```

- When deployed on Render (`RENDER=true` or `APP_ENV=production`), the application **strictly forbids SQLite**.
- If the PostgreSQL instance provided by Render's environment variable `DATABASE_URL` is unreachable or unconfigured, the server fails fast with a `RuntimeError` rather than falling back to an unpersisted local file.

---

## 4. What Was Tested vs What Was Not Tested

| Database Target | Connection Tested? | Table Creation Tested? | Persistence Tested? | Formal Status | Evidence |
|:---|:---:|:---:|:---:|:---:|:---|
| **Local SQLite (`clinical_local.db`)** | Yes | Yes (6 tables) | Yes | ✅ **PASSED** | `tests/test_phase9_e2e_integration.py` & `test_full_stack_e2e_workflows.py` |
| **Local PostgreSQL (`localhost:5433`)** | No (Offline) | No | No | ⚠️ **NOT TESTED** | Port 5433 closed; service stopped on host |
| **Render Cloud PostgreSQL** | No | No | No | ⚠️ **NOT TESTED** | Requires active Render deployment |

> [!CAUTION]
> **Strict Reporting Standard:**
> We do NOT claim PostgreSQL has passed local testing. Local testing passed exclusively on the SQLite development fallback engine. PostgreSQL verification must be performed once the PostgreSQL service is started locally or during initial staging on Render.
