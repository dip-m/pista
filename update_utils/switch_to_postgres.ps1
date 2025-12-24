# PowerShell script to switch from SQLite to PostgreSQL
# Usage: .\update_utils\switch_to_postgres.ps1 -PostgresUrl "postgresql://user:pass@host:5432/db"

param(
    [Parameter(Mandatory=$true)]
    [string]$PostgresUrl,
    
    [string]$SqliteDb = "gen/bgg_semantic.db"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Switching to PostgreSQL" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "SQLite Database: $SqliteDb"
Write-Host "PostgreSQL URL: $PostgresUrl"
Write-Host ""

# Backup SQLite
if (Test-Path $SqliteDb) {
    Write-Host "Creating backup of SQLite database..." -ForegroundColor Yellow
    $backupName = "$SqliteDb.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $SqliteDb $backupName
    Write-Host "✅ Backup created: $backupName" -ForegroundColor Green
}

# Check if psycopg2 is installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import psycopg2" 2>$null
    Write-Host "✅ psycopg2 is installed" -ForegroundColor Green
} catch {
    Write-Host "Installing psycopg2-binary..." -ForegroundColor Yellow
    pip install psycopg2-binary
}

# Run migration
Write-Host ""
Write-Host "Running migration..." -ForegroundColor Yellow
python update_utils/migrate_to_postgres.py `
    --sqlite-db $SqliteDb `
    --postgres-url $PostgresUrl

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migration failed!" -ForegroundColor Red
    exit 1
}

# Verify
Write-Host ""
Write-Host "Verifying PostgreSQL connection..." -ForegroundColor Yellow
python update_utils/verify_postgres.py --postgres-url $PostgresUrl

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Migration Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update your .env file:"
Write-Host "   DB_TYPE=postgres"
Write-Host "   DATABASE_URL=$PostgresUrl"
Write-Host ""
Write-Host "2. Restart your backend server"
Write-Host ""
