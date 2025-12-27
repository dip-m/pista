# Testing Framework Setup Guide

This guide will help you set up and use the comprehensive testing framework for the Pista project.

## Quick Start

### 1. Initial Setup

**Linux/Mac:**
```bash
./scripts/setup_testing.sh
```

**Windows:**
```powershell
.\scripts\setup_testing.ps1
```

This will:
- Install Python test dependencies
- Install frontend dependencies
- Set up pre-commit hooks
- Make scripts executable

### 2. Verify Installation

**Backend tests:**
```bash
pytest backend/tests/unit/ -v
```

**Frontend tests:**
```bash
cd frontend
npm test
```

## Pre-commit Hooks

Pre-commit hooks automatically run before each commit. They will:
- Check code formatting (Black, ESLint)
- Run linting (Flake8, ESLint)
- Run unit and integration tests
- Block commits if tests fail

### Install Hooks
```bash
pre-commit install
```

### Run Manually
```bash
pre-commit run --all-files
```

### Skip Hooks (Not Recommended)
```bash
git commit --no-verify
```

## Running Tests

### Backend Tests

```bash
# All tests
pytest

# Unit tests only
pytest backend/tests/unit/

# Integration tests only
pytest backend/tests/integration/

# Feature tests only
pytest backend/tests/feature/

# With coverage
pytest --cov=backend --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:ci

# Watch mode
npm run test:watch
```

## GitHub Actions CI

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

View results in the "Actions" tab on GitHub.

## Database Sync

### Manual Sync

```bash
# Full sync all tables
python scripts/sync_db_production.py --full-sync

# Sync specific tables
python scripts/sync_db_production.py --tables games,users

# Incremental sync (last 7 days)
python scripts/sync_db_production.py --incremental --tables games,users

# Dry run (see what would sync)
python scripts/sync_db_production.py --dry-run
```

### Environment Variables

Set these before running sync:

```bash
# Production database (read-only recommended)
export PROD_DATABASE_URL="postgresql://user:pass@prod-host:5432/dbname"

# Local database
export DATABASE_URL="postgresql://user:pass@localhost:5432/pista_local"
```

### Scheduled Sync

**Linux/Mac (Cron):**
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * /path/to/project/scripts/sync_db_schedule.sh
```

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 2:00 AM
4. Action: Start a program
5. Program: `powershell.exe`
6. Arguments: `-File "C:\path\to\project\scripts\sync_db_schedule.ps1"`

## Coverage Reports

### View Coverage

**Backend:**
```bash
pytest --cov=backend --cov-report=html
# Open htmlcov/index.html in browser
```

**Frontend:**
```bash
cd frontend
npm run test:ci
# Open coverage/index.html in browser
```

### Coverage Goals

- **Backend**: Minimum 60% coverage
- **Frontend**: Minimum 50% coverage

CI will fail if coverage is below these thresholds.

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Python/Node versions match CI
- Verify environment variables are set
- Ensure test database is accessible

### Pre-commit Hooks Not Running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Database Sync Fails

- Verify `PROD_DATABASE_URL` and `DATABASE_URL` are set correctly
- Check network connectivity to production database
- Ensure production database allows connections
- Review logs in `logs/db_sync.log`

### Coverage Below Threshold

1. Review coverage report to find untested code
2. Add tests for missing coverage
3. Focus on critical paths first

## Best Practices

1. **Write tests first** (TDD) or alongside code
2. **Keep tests fast** - unit tests should be < 1 second
3. **Test edge cases** - not just happy paths
4. **Mock external services** - don't hit real APIs
5. **Update tests** when changing code
6. **Run tests before committing** - use pre-commit hooks

## Additional Resources

- See `TESTING.md` for detailed documentation
- See `.github/workflows/` for CI configuration
- See `pytest.ini` for pytest configuration
- See `frontend/jest.config.js` for Jest configuration
