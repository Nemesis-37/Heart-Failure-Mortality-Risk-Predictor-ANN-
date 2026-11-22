@echo off
title Migrate Database to PostgreSQL
echo ========================================================
echo Migrating Heart Failure Mortality Risk Predictor Data
echo Source: clinical_local.db (SQLite)
echo Target: PostgreSQL (localhost:5433 / heartmortality)
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Executing Data Migration Script...
python scripts/migrate_to_postgresql.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Migration failed. Check error output above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Running Complete E2E Verification Suite...
python scripts/test_postgresql_e2e_verification.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Verification reported issues. Check output above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo POSTGRESQL MIGRATION AND VERIFICATION COMPLETED!
echo ========================================================
pause
