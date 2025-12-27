#!/bin/bash
# Bash script to prepare codebase for deployment
# Usage: ./scripts/prepare-deployment.sh

set -e

echo "Preparing Pista for deployment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env 2>/dev/null || echo "Please create .env file manually"
    echo "Please edit .env and fill in your values!"
fi

# Check if frontend .env.production exists
if [ ! -f frontend/.env.production ]; then
    echo "Creating frontend/.env.production from template..."
    cp frontend/.env.production.example frontend/.env.production 2>/dev/null || echo "Please create frontend/.env.production manually"
    echo "Please edit frontend/.env.production and set REACT_APP_API_BASE_URL!"
fi

# Check database
if [ ! -f gen/bgg_semantic.db ]; then
    echo "WARNING: Database file not found at gen/bgg_semantic.db"
    echo "Please ensure the database file exists before deployment!"
fi

# Check FAISS index
if [ ! -f gen/game_vectors.index ]; then
    echo "WARNING: FAISS index not found at gen/game_vectors.index"
    echo "Please ensure the index file exists before deployment!"
fi

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and frontend/.env.production with your values"
echo "2. Deploy backend (see DEPLOYMENT_GUIDE.md)"
echo "3. Deploy frontend (see DEPLOYMENT_GUIDE.md)"
echo "4. Build mobile app (see DEPLOYMENT_GUIDE.md)"
