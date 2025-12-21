# PowerShell script to prepare codebase for deployment
# Usage: .\scripts\prepare-deployment.ps1

Write-Host "Preparing Pista for deployment..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env" -ErrorAction SilentlyContinue
    Write-Host "Please edit .env and fill in your values!" -ForegroundColor Yellow
}

# Check if frontend .env.production exists
if (-not (Test-Path "frontend\.env.production")) {
    Write-Host "Creating frontend/.env.production from template..." -ForegroundColor Yellow
    Copy-Item "frontend\.env.production.example" "frontend\.env.production" -ErrorAction SilentlyContinue
    Write-Host "Please edit frontend/.env.production and set REACT_APP_API_BASE_URL!" -ForegroundColor Yellow
}

# Check database
if (-not (Test-Path "gen\bgg_semantic.db")) {
    Write-Host "WARNING: Database file not found at gen\bgg_semantic.db" -ForegroundColor Red
    Write-Host "Please ensure the database file exists before deployment!" -ForegroundColor Red
}

# Check FAISS index
if (-not (Test-Path "gen\game_vectors.index")) {
    Write-Host "WARNING: FAISS index not found at gen\game_vectors.index" -ForegroundColor Red
    Write-Host "Please ensure the index file exists before deployment!" -ForegroundColor Red
}

# Install frontend dependencies
Write-Host "Installing frontend dependencies..." -ForegroundColor Green
Set-Location frontend
npm install
Set-Location ..

Write-Host "`nDeployment preparation complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env and frontend/.env.production with your values" -ForegroundColor White
Write-Host "2. Deploy backend (see DEPLOYMENT_GUIDE.md)" -ForegroundColor White
Write-Host "3. Deploy frontend (see DEPLOYMENT_GUIDE.md)" -ForegroundColor White
Write-Host "4. Build mobile app (see DEPLOYMENT_GUIDE.md)" -ForegroundColor White

