#!/bin/bash
# Start script for Pista Backend
# Usage: ./start-backend.sh [dev|prod]

ENV=${1:-dev}

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    echo "Usage: ./start-backend.sh [dev|prod]"
    echo "Default: dev"
    exit 1
fi

echo "Starting Pista Backend in $ENV mode..."

# Load environment variables from .env file
if [ -f ".env.$ENV" ]; then
    echo "Loading environment variables from .env.$ENV..."
    set -a
    source .env.$ENV
    set +a
else
    # On Render/cloud platforms, env vars are set via platform config
    # This is expected and not an error
    if [ "$ENV" = "prod" ] && [ -n "$RENDER" ] || [ -n "$DATABASE_URL" ]; then
        echo "Using system environment variables (expected on Render/cloud platforms)."
    else
        echo "Warning: .env.$ENV not found. Using system environment variables."
        echo "Please create .env.$ENV file. See ENV_SETUP.md for details."
    fi
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check if uvicorn is installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "Installing uvicorn..."
    pip install uvicorn[standard]
fi

# Start the server
echo "Starting backend server on $API_HOST:$API_PORT..."
echo "Database: $DB_TYPE"
if [ "$DB_TYPE" = "postgres" ]; then
    echo "PostgreSQL URL: $DATABASE_URL"
fi

# Set environment variable to exclude directories from watchfiles (backup)
export WATCHFILES_IGNORE_PATHS="venv:.git:__pycache__:*.pyc:gen:logs:node_modules"

# Start with uvicorn
# Only watch backend directory - main.py and db.py are now in backend/
# This completely avoids watching venv and root directory
# On production (Render), don't use --reload and use $PORT from environment
if [ "$ENV" = "prod" ]; then
    uvicorn backend.main:app \
        --host "${API_HOST:-0.0.0.0}" \
        --port "${API_PORT:-$PORT}"
else
    uvicorn backend.main:app \
        --host "${API_HOST:-0.0.0.0}" \
        --port "${API_PORT:-8000}" \
        --reload \
        --reload-dir backend
fi
