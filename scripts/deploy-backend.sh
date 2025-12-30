#!/bin/bash
# Backend Deployment Script
# Usage: ./scripts/deploy-backend.sh [environment]

set -e

ENVIRONMENT=${1:-production}
echo "Deploying backend for environment: $ENVIRONMENT"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create it from .env.example"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Warning: Database file not found at $DB_PATH"
    echo "Please ensure bgg_semantic.db is in the gen/ directory"
fi

# Check if FAISS index exists
if [ ! -f "./gen/game_vectors.index" ]; then
    echo "Warning: FAISS index not found at ./gen/game_vectors.index"
    echo "Please ensure game_vectors.index is in the gen/ directory"
fi

# Install/update dependencies
echo "Installing Python dependencies..."
pip install -r update_utils/requirements.txt

# Run database migrations if needed
echo "Checking database schema..."
python -c "from db import ensure_schema, db_connection, DB_PATH; conn = db_connection(DB_PATH); ensure_schema(conn); conn.close()"

# Start the server
echo "Starting Pista backend server..."
# Use python -m uvicorn to avoid launcher path issues
if [ "$ENVIRONMENT" = "production" ]; then
    python -m uvicorn backend.main:app --host 0.0.0.0 --port ${API_PORT:-8000} --workers 4
else
    python -m uvicorn backend.main:app --host 0.0.0.0 --port ${API_PORT:-8000} --reload
fi
