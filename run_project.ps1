# CardioPredict - Heart Failure Mortality Risk Predictor Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting Heart Failure Mortality Risk Predictor Services" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "`n[1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "[2/2] Starting React Frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir\frontend'; npm run dev"

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "Services running!" -ForegroundColor Green
Write-Host "Backend API:  http://127.0.0.1:8000 (Swagger: /docs)" -ForegroundColor White
Write-Host "Frontend App: http://localhost:5173" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan
