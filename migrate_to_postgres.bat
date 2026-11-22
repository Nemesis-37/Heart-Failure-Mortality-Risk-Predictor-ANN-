@echo off
title CardioPredict - PostgreSQL Migration and Full Verification
echo ======================================================================
echo  CardioPredict - PostgreSQL Database Migration & Full E2E Verification
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Running PostgreSQL Data Migration Script...
python scripts/migrate_to_postgresql.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PostgreSQL data migration failed. Check credentials above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Running Database Schema & Record Verification...
python scripts/test_postgresql_e2e_verification.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Verification reported issues.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Running Full-Stack E2E Application Workflows...
python tests/test_full_stack_e2e_workflows.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Workflow verification failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ======================================================================
echo [SUCCESS] PostgreSQL Integration and Full E2E Verification Complete!
echo ======================================================================
pause
