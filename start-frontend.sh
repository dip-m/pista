#!/bin/bash
# Start script for Pista Frontend
# Usage: ./start-frontend.sh [dev|prod]

ENV=${1:-dev}

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    echo "Usage: ./start-frontend.sh [dev|prod]"
    echo "Default: dev"
    exit 1
fi

echo "Starting Pista Frontend in $ENV mode..."

# Change to frontend directory
cd frontend || exit 1

# Load environment variables from .env file
if [ -f ".env.$ENV" ]; then
    echo "Loading environment variables from .env.$ENV..."
    # Copy .env file to .env for React to use
    cp ".env.$ENV" .env
    echo "Environment file loaded."
else
    echo "Warning: .env.$ENV not found. Using default environment variables."
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the development server
echo "Starting frontend server..."
if [ "$ENV" = "dev" ]; then
    npm start
else
    npm run build
    npm run serve
fi
