# Scheduled database sync script for Windows
# Use Task Scheduler to run this periodically

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogFile = Join-Path $ProjectRoot "logs\db_sync.log"
$PythonEnv = Join-Path $ProjectRoot "venv\Scripts\python.exe"

# Create logs directory if it doesn't exist
$LogDir = Split-Path -Parent $LogFile
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Determine Python command
if (Test-Path $PythonEnv) {
    $PythonCmd = $PythonEnv
} else {
    $PythonCmd = "python"
}

# Run sync (incremental sync daily)
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "$Timestamp`: Starting database sync..."

Set-Location $ProjectRoot
& $PythonCmd "$ScriptDir\sync_db_production.py" --incremental --tables games,users,user_collections | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -eq 0) {
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$Timestamp`: Database sync completed successfully"
} else {
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$Timestamp`: ERROR: Database sync failed"
    # Optional: Send notification
}
