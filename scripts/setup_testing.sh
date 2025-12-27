#!/bin/bash
# Setup script for testing framework
# Run this once to set up the testing environment

set -e

echo "Setting up Pista testing framework..."

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Install Python test dependencies
echo "Installing Python test dependencies..."
pip install -r requirements-test.txt

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pip install pre-commit
pre-commit install

# Make sync scripts executable
chmod +x scripts/sync_db_schedule.sh
chmod +x scripts/sync_db_production.py

echo ""
echo "✓ Testing framework setup complete!"
echo ""
echo "Next steps:"
echo "1. Run backend tests: pytest"
echo "2. Run frontend tests: cd frontend && npm test"
echo "3. Try a commit to test pre-commit hooks"
echo "4. Configure database sync: Set PROD_DATABASE_URL and DATABASE_URL environment variables"
