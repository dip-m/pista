# Start script for Pista Frontend (PowerShell)
# Usage: .\start-frontend.ps1 [dev|prod]

param(
    [string]$Env = "dev"
)

if ($Env -ne "dev" -and $Env -ne "prod") {
    Write-Host "Usage: .\start-frontend.ps1 [dev|prod]" -ForegroundColor Red
    Write-Host "Default: dev"
    exit 1
}

Write-Host "Starting Pista Frontend in $Env mode..." -ForegroundColor Green

# Change to frontend directory
Set-Location frontend

# Load environment variables from .env file
$envFile = ".env.$Env"
if (Test-Path $envFile) {
    Write-Host "Loading environment variables from $envFile..." -ForegroundColor Cyan
    # Copy .env file to .env for React to use
    Copy-Item $envFile .env -Force
    Write-Host "Environment file loaded." -ForegroundColor Green
} else {
    Write-Host "Warning: $envFile not found. Using default environment variables." -ForegroundColor Yellow
}

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    npm install
}

# Start the development server
Write-Host "Starting frontend server..." -ForegroundColor Green
if ($Env -eq "dev") {
    npm start
} else {
    npm run build
    npm run serve
}
