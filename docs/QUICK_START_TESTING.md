# Quick Start: Testing Framework

## 🚀 One-Command Setup

**Linux/Mac:**
```bash
./scripts/setup_testing.sh
```

**Windows:**
```powershell
.\scripts\setup_testing.ps1
```

## ✅ Verify It Works

```bash
# Backend tests
pytest backend/tests/unit/ -v

# Frontend tests  
cd frontend && npm test
```

## 📝 How It Works

### Pre-commit Hooks
- Automatically run before every commit
- Block commits if tests fail
- Run formatting, linting, and tests

### GitHub Actions
- Automatically run on push/PR
- Generate coverage reports
- Enforce coverage thresholds

### Database Sync
```bash
# Set environment variables first
export PROD_DATABASE_URL="postgresql://..."
export DATABASE_URL="postgresql://..."

# Sync
python scripts/sync_db_production.py --incremental
```

## 📚 Full Documentation

- `TESTING.md` - Complete testing guide
- `README_TESTING.md` - Setup and usage
- `SETUP_TESTING_SUMMARY.md` - Implementation summary

## 🎯 Coverage Goals

- Backend: 60% minimum
- Frontend: 50% minimum

Add tests incrementally to reach these goals!
