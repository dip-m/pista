# Deployment Scripts

This directory contains scripts to help with deployment.

## Available Scripts

### `prepare-deployment.sh` / `prepare-deployment.ps1`
Prepares the codebase for deployment by:
- Checking for required files (database, index)
- Creating environment file templates
- Installing dependencies

**Usage:**
```bash
# Linux/Mac
./scripts/prepare-deployment.sh

# Windows PowerShell
.\scripts\prepare-deployment.ps1
```

### `deploy-backend.sh`
Deploys the backend server (for Linux/Mac servers).

**Usage:**
```bash
./scripts/deploy-backend.sh [production|development]
```

### `deploy-frontend.sh`
Builds the frontend for production deployment.

**Usage:**
```bash
./scripts/deploy-frontend.sh [production|development]
```

### `build-android.sh`
Builds the Android APK.

**Usage:**
```bash
./scripts/build-android.sh
```

## Notes

- Make scripts executable on Linux/Mac: `chmod +x scripts/*.sh`
- PowerShell scripts work on Windows
- All scripts should be run from the project root directory

