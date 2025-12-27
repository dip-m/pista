# Setup script for testing framework (Windows PowerShell)
# Run this once to set up the testing environment

$ErrorActionPreference = "Stop"

Write-Host "Setting up Pista testing framework..." -ForegroundColor Green

# Get project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

# Install Python test dependencies
Write-Host "Installing Python test dependencies..." -ForegroundColor Yellow
pip install -r requirements-test.txt

# Install frontend dependencies
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm install
Set-Location ..

# Install pre-commit hooks
Write-Host "Installing pre-commit hooks..." -ForegroundColor Yellow
pip install pre-commit
pre-commit install

Write-Host ""
Write-Host "✓ Testing framework setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run backend tests: pytest"
Write-Host "2. Run frontend tests: cd frontend && npm test"
Write-Host "3. Try a commit to test pre-commit hooks"
Write-Host "4. Configure database sync: Set PROD_DATABASE_URL and DATABASE_URL environment variables"
