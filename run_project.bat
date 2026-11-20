@echo off
title Heart Failure Mortality Risk Predictor Launcher
echo ========================================================
echo Starting Heart Failure Mortality Risk Predictor Services
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "CardioPredict Backend (FastAPI)" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting React Frontend on http://localhost:5173 ...
start "CardioPredict Frontend (Vite React)" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo Both services launched in separate windows!
echo Backend:  http://127.0.0.1:8000 (API & Docs at /docs)
echo Frontend: http://localhost:5173
echo ========================================================
echo.
pause
