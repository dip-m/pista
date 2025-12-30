#!/bin/bash
# Start script for Pista Backend
# Usage: ./start-backend.sh [dev|prod]
# This script should be run from the project root directory

ENV=${1:-dev}

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    echo "Usage: ./start-backend.sh [dev|prod]"
    echo "Default: dev"
    exit 1
fi

echo "Starting Pista Backend in $ENV mode..."
echo "Working directory: $(pwd)"

# Ensure we're in the project root (where backend/ folder exists)
if [ ! -d "backend" ]; then
    echo "Error: backend/ folder not found. Please run this script from the project root."
    exit 1
fi

# Load environment variables from .env file in root directory
if [ -f ".env.$ENV" ]; then
    echo "Loading environment variables from .env.$ENV..."
    set -a
    source .env.$ENV
    set +a
    echo "Environment variables loaded from .env.$ENV"
else
    # On Render/cloud platforms, env vars are set via platform config
    # This is expected and not an error
    if [ "$ENV" = "prod" ] && ([ -n "$RENDER" ] || [ -n "$DATABASE_URL" ]); then
        echo "Using system environment variables (expected on Render/cloud platforms)."
    else
        echo "Warning: .env.$ENV not found in root directory."
        echo "Please create .env.$ENV based on env.template.dev"
        echo "Using system environment variables (if set)."
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

# Start with uvicorn
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"

# Set environment variable to exclude directories from watchfiles (backup)
export WATCHFILES_IGNORE_PATHS="venv:.git:__pycache__:*.pyc:gen:logs:node_modules:frontend"

# Display configuration
echo ""
echo "Backend Configuration:"
echo "  Host: $API_HOST"
echo "  Port: $API_PORT"
echo "  Database: ${DB_TYPE:-not set}"
if [ "$DB_TYPE" = "postgres" ] && [ -n "$DATABASE_URL" ]; then
    # Mask password in URL for display
    MASKED_URL=$(echo "$DATABASE_URL" | sed 's|://\([^:]*\):[^@]*@|://\1:***@|')
    echo "  Database URL: $MASKED_URL"
fi
echo "  Environment: $ENV"
echo ""

# Use python -m uvicorn to avoid launcher path issues
# Only watch backend directory - main.py and db.py are now in backend/
# This completely avoids watching venv and root directory
# On production (Render), don't use --reload and use $PORT from environment
if [ "$ENV" = "prod" ]; then
    echo "Starting uvicorn in production mode..."
    echo "Command: python -m uvicorn backend.main:app --host $API_HOST --port ${API_PORT:-$PORT}"
    python -m uvicorn backend.main:app \
        --host "$API_HOST" \
        --port "${API_PORT:-$PORT}"
else
    echo "Starting uvicorn with auto-reload..."
    echo "Command: python -m uvicorn backend.main:app --host $API_HOST --port $API_PORT --reload --reload-dir backend"
    python -m uvicorn backend.main:app \
        --host "$API_HOST" \
        --port "$API_PORT" \
        --reload \
        --reload-dir backend
fi
