#!/bin/bash
# Scheduled database sync script
# Add to crontab: 0 2 * * * /path/to/scripts/sync_db_schedule.sh

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/db_sync.log"
PYTHON_ENV="$PROJECT_ROOT/venv/bin/python"

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Activate virtual environment if it exists
if [ -f "$PYTHON_ENV" ]; then
    PYTHON_CMD="$PYTHON_ENV"
else
    PYTHON_CMD="python3"
fi

# Run sync (incremental sync daily)
echo "$(date): Starting database sync..." >> "$LOG_FILE"
cd "$PROJECT_ROOT"
$PYTHON_CMD "$SCRIPT_DIR/sync_db_production.py" --incremental --tables games,users,user_collections >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): Database sync completed successfully" >> "$LOG_FILE"
else
    echo "$(date): ERROR: Database sync failed" >> "$LOG_FILE"
    # Optional: Send notification (email, Slack, etc.)
fi
