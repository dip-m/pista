#!/bin/bash
# Start script for Pista Frontend
# Usage: ./start-frontend.sh [dev|prod]
# This script should be run from the project root directory

ENV=${1:-dev}

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    echo "Usage: ./start-frontend.sh [dev|prod]"
    echo "Default: dev"
    exit 1
fi

echo "Starting Pista Frontend in $ENV mode..."
echo "Working directory: $(pwd)"

# Ensure we're in the project root (where frontend/ folder exists)
if [ ! -d "frontend" ]; then
    echo "Error: frontend/ folder not found. Please run this script from the project root."
    exit 1
fi

# Store original directory
ORIGINAL_DIR=$(pwd)

# Change to frontend directory
cd frontend || exit 1

# Load environment variables from .env file in frontend directory
if [ -f ".env.$ENV" ]; then
    echo "Loading environment variables from frontend/.env.$ENV..."
    # Copy .env file to .env for React to use (React Scripts reads .env)
    cp ".env.$ENV" .env
    echo "Environment file loaded."
else
    echo "Warning: frontend/.env.$ENV not found."
    echo "Please create frontend/.env.$ENV based on frontend/env.template.dev"
    echo "Using default environment variables (API will be http://localhost:8000)"
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies (this may take a few minutes)..."
    npm install
    if [ $? -ne 0 ]; then
        echo "Error: npm install failed"
        cd "$ORIGINAL_DIR"
        exit 1
    fi
fi

# Display configuration
echo ""
echo "Frontend Configuration:"
if [ -f ".env" ]; then
    API_BASE=$(grep "REACT_APP_API_BASE_URL" .env | cut -d '=' -f2)
    echo "  API Base URL: ${API_BASE:-http://localhost:8000 (default)}"
else
    echo "  API Base URL: http://localhost:8000 (default)"
fi
echo "  Environment: $ENV"
echo ""

# Start the development server
if [ "$ENV" = "dev" ]; then
    echo "Starting frontend server..."
    echo "Development server will start on http://localhost:3000"
    echo "Press Ctrl+C to stop"
    echo ""
    npm start
else
    echo "Building for production..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "Error: Build failed"
        cd "$ORIGINAL_DIR"
        exit 1
    fi
    echo "Starting production server on http://localhost:3000"
    npm run serve
fi

# Return to original directory on exit
cd "$ORIGINAL_DIR"
