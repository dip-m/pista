#!/bin/bash
# Quick script to switch from SQLite to PostgreSQL
# Usage: ./update_utils/switch_to_postgres.sh <postgres_url>

set -e

POSTGRES_URL="${1:-}"

if [ -z "$POSTGRES_URL" ]; then
    echo "Usage: $0 <postgres_url>"
    echo "Example: $0 postgresql://user:pass@localhost:5432/pista"
    exit 1
fi

SQLITE_DB="${SQLITE_DB:-gen/bgg_semantic.db}"

echo "=========================================="
echo "Switching to PostgreSQL"
echo "=========================================="
echo ""
echo "SQLite Database: $SQLITE_DB"
echo "PostgreSQL URL: $POSTGRES_URL"
echo ""

# Backup SQLite
if [ -f "$SQLITE_DB" ]; then
    echo "Creating backup of SQLite database..."
    cp "$SQLITE_DB" "${SQLITE_DB}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup created"
fi

# Check if psycopg2 is installed
echo "Checking dependencies..."
python -c "import psycopg2" 2>/dev/null || {
    echo "Installing psycopg2-binary..."
    pip install psycopg2-binary
}

# Run migration
echo ""
echo "Running migration..."
python update_utils/migrate_to_postgres.py \
    --sqlite-db "$SQLITE_DB" \
    --postgres-url "$POSTGRES_URL"

# Verify
echo ""
echo "Verifying PostgreSQL connection..."
python update_utils/verify_postgres.py --postgres-url "$POSTGRES_URL"

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update your .env file:"
echo "   DB_TYPE=postgres"
echo "   DATABASE_URL=$POSTGRES_URL"
echo ""
echo "2. Restart your backend server"
echo ""
