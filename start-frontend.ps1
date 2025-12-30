# Start script for Pista Frontend (PowerShell)
# Usage: .\start-frontend.ps1 [dev|prod]
# This script should be run from the project root directory

param(
    [string]$Env = "dev"
)

if ($Env -ne "dev" -and $Env -ne "prod") {
    Write-Host "Usage: .\start-frontend.ps1 [dev|prod]" -ForegroundColor Red
    Write-Host "Default: dev" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Pista Frontend in $Env mode..." -ForegroundColor Green
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Cyan

# Ensure we're in the project root (where frontend/ folder exists)
if (-not (Test-Path "frontend")) {
    Write-Host "Error: frontend/ folder not found. Please run this script from the project root." -ForegroundColor Red
    exit 1
}

# Store original directory
$originalDir = Get-Location

# Change to frontend directory
Set-Location frontend

try {
    # Load environment variables from .env file in frontend directory
    $envFile = ".env.$Env"
    if (Test-Path $envFile) {
        Write-Host "Loading environment variables from frontend/$envFile..." -ForegroundColor Cyan
        # Copy .env file to .env for React to use (React Scripts reads .env)
        Copy-Item $envFile .env -Force
        Write-Host "Environment file loaded." -ForegroundColor Green
    } else {
        Write-Host "Warning: frontend/$envFile not found." -ForegroundColor Yellow
        Write-Host "Please create frontend/$envFile based on frontend/env.template.dev" -ForegroundColor Yellow
        Write-Host "Using default environment variables (API will be http://localhost:8000)" -ForegroundColor Yellow
    }

    # Check if node_modules exists
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Cyan
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: npm install failed" -ForegroundColor Red
            Set-Location $originalDir
            exit 1
        }
    }

    # Display configuration
    Write-Host "`nFrontend Configuration:" -ForegroundColor Cyan
    if (Test-Path ".env") {
        $apiBase = (Get-Content .env | Select-String "REACT_APP_API_BASE_URL").ToString() -replace "REACT_APP_API_BASE_URL=", ""
        Write-Host "  API Base URL: $apiBase" -ForegroundColor White
    } else {
        Write-Host "  API Base URL: http://localhost:8000 (default)" -ForegroundColor White
    }
    Write-Host "  Environment: $Env" -ForegroundColor White
    Write-Host ""

    # Start the development server
    Write-Host "Starting frontend server..." -ForegroundColor Green
    if ($Env -eq "dev") {
        Write-Host "Development server will start on http://localhost:3000" -ForegroundColor Cyan
        Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
        Write-Host ""
        npm start
    } else {
        Write-Host "Building for production..." -ForegroundColor Cyan
        npm run build
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Build failed" -ForegroundColor Red
            Set-Location $originalDir
            exit 1
        }
        Write-Host "Starting production server on http://localhost:3000" -ForegroundColor Cyan
        npm run serve
    }
} finally {
    # Return to original directory
    Set-Location $originalDir
}
