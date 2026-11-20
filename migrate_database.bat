@echo off
title Migrate SQLite to Microsoft SQL Server
echo ========================================================
echo Migrating Heart Failure Mortality Risk Predictor Data
echo Source: clinical_local.db (SQLite)
echo Target: DESKTOP-NA0D6N1\SQLEXPRESS (HeartMortalityPredictor)
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Executing Data Migration Script...
python scripts/migrate_sqlite_to_sqlserver.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Migration failed. Check error output above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Running Complete E2E Verification Suite...
python scripts/test_sqlserver_e2e_verification.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Verification reported issues. Check output above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================================
echo MIGRATION AND E2E VERIFICATION COMPLETED SUCCESSFULLY!
echo ========================================================
pause
