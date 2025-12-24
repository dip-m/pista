# Environment Setup Guide

This guide explains how to set up environment variables for different environments.

## Environment Files

Create the following environment files in the project root:

### `.env.dev` (Development)
```env
# Development Environment Variables
# Backend Configuration
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# Database - PostgreSQL (Local)
DB_TYPE=postgres
DATABASE_URL=postgresql://postgres:admin@localhost:5432/pista
DB_PATH=./gen/bgg_semantic.db

# Security
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# OAuth Configuration
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
META_CLIENT_ID=
META_CLIENT_SECRET=
OAUTH_REDIRECT_BASE=http://localhost:3000

# API Keys
OPENAI_API_KEY=
REPLICATE_API_TOKEN=
BEARER_TOKEN=

# Logging
LOG_LEVEL=DEBUG
```

### `.env.prod` (Production)
```env
# Production Environment Variables
# Backend Configuration
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000

# CORS Configuration - Update with your production frontend URLs
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://www.your-frontend-domain.com

# Database - PostgreSQL (Production)
DB_TYPE=postgres
DATABASE_URL=postgresql://user:password@host:5432/database
DB_PATH=./gen/bgg_semantic.db

# Security - CHANGE THESE IN PRODUCTION!
JWT_SECRET_KEY=change-this-to-a-strong-random-secret-key-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# OAuth Configuration
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
META_CLIENT_ID=
META_CLIENT_SECRET=
OAUTH_REDIRECT_BASE=https://your-frontend-domain.com

# API Keys
OPENAI_API_KEY=
REPLICATE_API_TOKEN=
BEARER_TOKEN=

# Logging
LOG_LEVEL=INFO
```

## Frontend Environment Files

Create these files in the `frontend/` directory:

### `frontend/.env.dev`
```env
# Frontend Development Environment Variables
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_GOOGLE_CLIENT_ID=
REACT_APP_MICROSOFT_CLIENT_ID=
```

### `frontend/.env.prod`
```env
# Frontend Production Environment Variables
REACT_APP_API_BASE_URL=https://your-backend-api-domain.com
REACT_APP_GOOGLE_CLIENT_ID=
REACT_APP_MICROSOFT_CLIENT_ID=
```

## Usage

### Starting Backend

**Windows (PowerShell):**
```powershell
.\start-backend.ps1 dev    # Development mode
.\start-backend.ps1 prod   # Production mode
```

**Linux/Mac:**
```bash
chmod +x start-backend.sh
./start-backend.sh dev     # Development mode
./start-backend.sh prod    # Production mode
```

### Starting Frontend

**Windows (PowerShell):**
```powershell
.\start-frontend.ps1 dev    # Development mode
.\start-frontend.ps1 prod   # Production mode
```

**Linux/Mac:**
```bash
chmod +x start-frontend.sh
./start-frontend.sh dev     # Development mode
./start-frontend.sh prod    # Production mode
```

## Notes

- Environment files (`.env.*`) are gitignored for security
- Always use strong, unique secrets in production
- Update `ALLOWED_ORIGINS` with your actual frontend URLs
- For development, the backend uses PostgreSQL on localhost:5432
- Make sure PostgreSQL is running before starting the backend in dev mode

