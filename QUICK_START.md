# Quick Start Guide

## Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL (for development - running on localhost:5432)
- npm or yarn

## Initial Setup

1. **Create environment files from templates:**
   ```bash
   # Backend
   cp env.template.dev .env.dev
   cp env.template.prod .env.prod
   
   # Frontend
   cp frontend/env.template.dev frontend/.env.dev
   cp frontend/env.template.prod frontend/.env.prod
   ```

2. **Update `.env.dev` with your local PostgreSQL credentials:**
   ```env
   DATABASE_URL=postgresql://postgres:admin@localhost:5432/pista
   ```

3. **Make scripts executable (Linux/Mac):**
   ```bash
   chmod +x start-backend.sh start-frontend.sh
   ```

## Starting the Application

### Development Mode

**Backend (Terminal 1):**
```bash
# Windows PowerShell
.\start-backend.ps1 dev

# Linux/Mac
./start-backend.sh dev
```

**Frontend (Terminal 2):**
```bash
# Windows PowerShell
.\start-frontend.ps1 dev

# Linux/Mac
./start-frontend.sh dev
```

### Production Mode

**Backend:**
```bash
# Windows PowerShell
.\start-backend.ps1 prod

# Linux/Mac
./start-backend.sh prod
```

**Frontend:**
```bash
# Windows PowerShell
.\start-frontend.ps1 prod

# Linux/Mac
./start-frontend.sh prod
```

## What the Scripts Do

### Backend Start Script
- Loads environment variables from `.env.dev` or `.env.prod`
- Creates/activates Python virtual environment
- Installs dependencies from `requirements.txt`
- Starts the FastAPI server with uvicorn

### Frontend Start Script
- Loads environment variables from `frontend/.env.dev` or `frontend/.env.prod`
- Copies environment file to `.env` for React
- Installs npm dependencies if needed
- Starts the React development server (dev) or builds for production (prod)

## Environment Variables

See `ENV_SETUP.md` for detailed information about all environment variables.

## Troubleshooting

### Backend won't start
- Check that PostgreSQL is running: `psql -U postgres -d pista`
- Verify `.env.dev` exists and has correct `DATABASE_URL`
- Check that port 8000 is not in use

### Frontend won't start
- Check that backend is running on port 8000
- Verify `frontend/.env.dev` exists and has correct `REACT_APP_API_BASE_URL`
- Check that port 3000 is not in use

### Database connection errors
- Ensure PostgreSQL is running
- Verify database `pista` exists: `CREATE DATABASE pista;`
- Check credentials in `.env.dev`

