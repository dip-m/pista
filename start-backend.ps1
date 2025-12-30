# Start script for Pista Backend (PowerShell)
# Usage: .\start-backend.ps1 [dev|prod]
# This script should be run from the project root directory

param(
    [string]$Env = "dev"
)

if ($Env -ne "dev" -and $Env -ne "prod") {
    Write-Host "Usage: .\start-backend.ps1 [dev|prod]" -ForegroundColor Red
    Write-Host "Default: dev" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Pista Backend in $Env mode..." -ForegroundColor Green
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Cyan

# Ensure we're in the project root (where backend/ folder exists)
if (-not (Test-Path "backend")) {
    Write-Host "Error: backend/ folder not found. Please run this script from the project root." -ForegroundColor Red
    exit 1
}

# Load environment variables from .env file in root directory
$envFile = ".env.$Env"
if (Test-Path $envFile) {
    Write-Host "Loading environment variables from $envFile..." -ForegroundColor Cyan
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present (both single and double)
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "Environment variables loaded from $envFile" -ForegroundColor Green
} else {
    Write-Host "Warning: $envFile not found in root directory." -ForegroundColor Yellow
    Write-Host "Please create $envFile based on env.template.dev" -ForegroundColor Yellow
    Write-Host "Using system environment variables (if set)." -ForegroundColor Yellow
}

# Check if virtual environment exists and is valid
$venvPython = "venv\Scripts\python.exe"
$venvExists = Test-Path $venvPython

if (-not $venvExists) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
} else {
    # Check if venv Python points to correct location (avoid OneDrive/symlink issues)
    try {
        $venvPythonPath = (Resolve-Path $venvPython -ErrorAction Stop).Path
        $currentDir = (Resolve-Path "." -ErrorAction Stop).Path
        # Normalize paths for comparison
        $venvNormalized = $venvPythonPath.ToLower().Replace('\', '/')
        $currentNormalized = $currentDir.ToLower().Replace('\', '/')

        if (-not $venvNormalized.StartsWith($currentNormalized)) {
            Write-Host "Warning: Virtual environment appears to be from a different location." -ForegroundColor Yellow
            Write-Host "  Current directory: $currentDir" -ForegroundColor Yellow
            Write-Host "  Venv Python path: $venvPythonPath" -ForegroundColor Yellow
            Write-Host "Recreating virtual environment in current location..." -ForegroundColor Cyan
            Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue
            python -m venv venv
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Error: Failed to recreate virtual environment" -ForegroundColor Red
                exit 1
            }
            Write-Host "Virtual environment recreated successfully." -ForegroundColor Green
        }
    } catch {
        Write-Host "Warning: Could not verify venv location: $_" -ForegroundColor Yellow
        Write-Host "If you encounter issues, try deleting the venv folder and running the script again." -ForegroundColor Yellow
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Failed to activate virtual environment, continuing anyway..." -ForegroundColor Yellow
}

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

# Start with uvicorn
$apiHost = if ($env:API_HOST) { $env:API_HOST } else { "0.0.0.0" }
$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

# Set environment variable to exclude directories from watchfiles (backup)
$env:WATCHFILES_IGNORE_PATHS = "venv;.git;__pycache__;*.pyc;gen;logs;node_modules;frontend"

# Display configuration
Write-Host ""
Write-Host "Backend Configuration:" -ForegroundColor Cyan
Write-Host "  Host: $apiHost" -ForegroundColor White
Write-Host "  Port: $apiPort" -ForegroundColor White
Write-Host "  Database: $($env:DB_TYPE)" -ForegroundColor White
if ($env:DB_TYPE -eq "postgres") {
    $dbUrl = $env:DATABASE_URL
    if ($dbUrl) {
        # Mask password in URL for display - use simple string replacement
        if ($dbUrl -match '://([^:]+):([^@]+)@') {
            $parts = $dbUrl -split '://'
            $afterProtocol = $parts[1]
            $atIndex = $afterProtocol.IndexOf('@')
            if ($atIndex -gt 0) {
                $beforeAt = $afterProtocol.Substring(0, $atIndex)
                $afterAt = $afterProtocol.Substring($atIndex + 1)
                $colonIndex = $beforeAt.IndexOf(':')
                if ($colonIndex -gt 0) {
                    $username = $beforeAt.Substring(0, $colonIndex)
                    $maskedUrl = $parts[0] + "://$username`:***@" + $afterAt
                } else {
                    $maskedUrl = $dbUrl
                }
            } else {
                $maskedUrl = $dbUrl
            }
        } else {
            $maskedUrl = $dbUrl
        }
        Write-Host "  Database URL: $maskedUrl" -ForegroundColor White
    }
}
Write-Host "  Environment: $Env" -ForegroundColor White
Write-Host ""

# Log the command being executed
if ($Env -eq "dev") {
    Write-Host "Starting uvicorn with auto-reload..." -ForegroundColor Green
} else {
    Write-Host "Starting uvicorn in production mode..." -ForegroundColor Green
}

try {
    # Use python -m uvicorn instead of uvicorn directly to avoid launcher path issues
    # This works even if venv was created in a different location
    if ($Env -eq "dev") {
        Write-Host "Command: python -m uvicorn backend.main:app --host $apiHost --port $apiPort --reload --reload-dir backend" -ForegroundColor Cyan
        python -m uvicorn backend.main:app --host $apiHost --port $apiPort --reload --reload-dir backend
    } else {
        Write-Host "Command: python -m uvicorn backend.main:app --host $apiHost --port $apiPort" -ForegroundColor Cyan
        python -m uvicorn backend.main:app --host $apiHost --port $apiPort
    }
} catch {
    Write-Host ""
    Write-Host "Error starting uvicorn: $_" -ForegroundColor Red
    Write-Host "Error type: $($_.Exception.GetType().FullName)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Ensure virtual environment is activated" -ForegroundColor Yellow
    Write-Host "  2. Check that all dependencies are installed: pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host "  3. Verify .env.$Env file exists and has correct DATABASE_URL" -ForegroundColor Yellow
    Write-Host "  4. Check that backend/main.py exists" -ForegroundColor Yellow
    exit 1
}
