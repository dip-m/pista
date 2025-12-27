# Start script for Pista Backend (PowerShell)
# Usage: .\start-backend.ps1 [dev|prod]

param(
    [string]$Env = "dev"
)

if ($Env -ne "dev" -and $Env -ne "prod") {
    Write-Host "Usage: .\start-backend.ps1 [dev|prod]" -ForegroundColor Red
    Write-Host "Default: dev"
    exit 1
}

Write-Host "Starting Pista Backend in $Env mode..." -ForegroundColor Green

# Load environment variables from .env file
$envFile = ".env.$Env"
if (Test-Path $envFile) {
    Write-Host "Loading environment variables from $envFile..." -ForegroundColor Cyan
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Write-Host "Warning: $envFile not found. Using system environment variables." -ForegroundColor Yellow
}

# Check if virtual environment exists, create if not
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Install/update dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -q -r requirements.txt

# Check if uvicorn is installed
try {
    python -c "import uvicorn" 2>$null
} catch {
    Write-Host "Installing uvicorn..." -ForegroundColor Cyan
    pip install uvicorn[standard]
}

# Start the server
Write-Host "Starting backend server on $env:API_HOST:$env:API_PORT..." -ForegroundColor Green
Write-Host "Database: $env:DB_TYPE" -ForegroundColor Cyan
if ($env:DB_TYPE -eq "postgres") {
    Write-Host "PostgreSQL URL: $env:DATABASE_URL" -ForegroundColor Cyan
}

# Start with uvicorn
$apiHost = if ($env:API_HOST) { $env:API_HOST } else { "0.0.0.0" }
$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

# Set environment variable to exclude directories from watchfiles (backup)
$env:WATCHFILES_IGNORE_PATHS = "venv;.git;__pycache__;*.pyc;gen;logs;node_modules"

# Log the command being executed
Write-Host "Executing: uvicorn backend.main:app --host $apiHost --port $apiPort --reload --reload-dir backend" -ForegroundColor Cyan

try {
    # Only watch backend directory - main.py and db.py are now in backend/
    # This completely avoids watching venv and root directory
    $uvicornArgs = @(
        "backend.main:app",
        "--host", $apiHost,
        "--port", $apiPort,
        "--reload",
        "--reload-dir", "backend"
    )

    # Execute uvicorn with array splatting to avoid wildcard expansion
    & uvicorn @uvicornArgs
} catch {
    Write-Host "Error starting uvicorn: $_" -ForegroundColor Red
    Write-Host "Error type: $($_.Exception.GetType().FullName)" -ForegroundColor Red
    Write-Host "Command was: uvicorn backend.main:app --host $apiHost --port $apiPort --reload --reload-dir backend" -ForegroundColor Yellow
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Yellow
    throw
}
