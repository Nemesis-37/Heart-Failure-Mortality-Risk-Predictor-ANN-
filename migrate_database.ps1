# ========================================================
# Migrate Database to PostgreSQL
# Source: clinical_local.db (SQLite)
# Target: PostgreSQL (localhost:5433 / heartmortality)
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Migrating Heart Failure Mortality Risk Predictor Data" -ForegroundColor Cyan
Write-Host "Source: clinical_local.db (SQLite)" -ForegroundColor Cyan
Write-Host "Target: PostgreSQL (localhost:5433 / heartmortality)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

Write-Host "[1/2] Executing Data Migration Script..." -ForegroundColor Yellow
python scripts/migrate_to_postgresql.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Migration failed. Check error output above." -ForegroundColor Red
    pause
    exit $LASTEXITCODE
}

Write-Host "`n[2/2] Running Complete PostgreSQL E2E Verification Suite..." -ForegroundColor Yellow
python scripts/test_postgresql_e2e_verification.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[WARNING] Verification reported issues. Check output above." -ForegroundColor Yellow
    pause
    exit $LASTEXITCODE
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "POSTGRESQL MIGRATION AND VERIFICATION COMPLETED!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
pause
