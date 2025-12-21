#!/bin/bash
# Frontend Deployment Script
# Usage: ./scripts/deploy-frontend.sh [environment]

set -e

ENVIRONMENT=${1:-production}
echo "Deploying frontend for environment: $ENVIRONMENT"

cd frontend

# Check if .env.production exists
if [ "$ENVIRONMENT" = "production" ] && [ ! -f .env.production ]; then
    echo "Warning: .env.production not found. Using defaults."
    echo "Please create .env.production with REACT_APP_API_BASE_URL"
fi

# Install dependencies
echo "Installing npm dependencies..."
npm install

# Build production bundle
echo "Building production bundle..."
npm run build

echo "Build complete! Files are in frontend/build/"
echo ""
echo "Next steps:"
echo "1. Deploy the 'build' directory to your hosting service"
echo "2. Ensure REACT_APP_API_BASE_URL is set correctly"
echo ""
echo "For Vercel: vercel --prod"
echo "For Netlify: netlify deploy --prod --dir=build"
echo "For AWS S3: aws s3 sync build/ s3://your-bucket-name --delete"

