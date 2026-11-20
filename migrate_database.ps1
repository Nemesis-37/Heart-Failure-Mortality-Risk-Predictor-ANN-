# CardioPredict - Migrate SQLite to Microsoft SQL Server
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Migrating Heart Failure Mortality Risk Predictor Data" -ForegroundColor Green
Write-Host "Source: clinical_local.db (SQLite)" -ForegroundColor White
Write-Host "Target: DESKTOP-NA0D6N1\SQLEXPRESS (HeartMortalityPredictor)" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "`n[1/2] Executing Data Migration Script..." -ForegroundColor Yellow
python scripts/migrate_sqlite_to_sqlserver.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Migration script reported an error (Exit Code: $LASTEXITCODE)." -ForegroundColor Red
    pause
    exit $LASTEXITCODE
}

Write-Host "`n[2/2] Running Complete E2E Verification Suite..." -ForegroundColor Yellow
python scripts/test_sqlserver_e2e_verification.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================================" -ForegroundColor Cyan
    Write-Host "ALL MIGRATION AND E2E CHECKS PASSED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host "SQL Server Express is now the active verified database." -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Cyan
} else {
    Write-Host "`n[WARNING] Verification checks exited with code $LASTEXITCODE." -ForegroundColor Yellow
}
