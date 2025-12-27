# Testing Framework Documentation

This document describes the comprehensive testing framework for the Pista project.

## Overview

The testing framework includes:
- **Unit Tests**: Test individual functions and components in isolation
- **Integration Tests**: Test API endpoints and component interactions
- **Feature Tests**: Test complete user flows end-to-end
- **Code Coverage**: Track and report test coverage for both backend and frontend

## Backend Testing

### Setup

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Run tests:
```bash
# Run all tests
pytest

# Run specific test categories
pytest backend/tests/unit/          # Unit tests only
pytest backend/tests/integration/   # Integration tests only
pytest backend/tests/feature/       # Feature tests only

# Run with coverage
pytest --cov=backend --cov-report=html
```

### Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_auth_utils.py
│   └── test_db.py
├── integration/             # Integration tests
│   ├── test_auth_endpoints.py
│   └── test_chat_endpoints.py
└── feature/                 # Feature tests
    └── test_user_flow.py
```

### Writing Backend Tests

#### Unit Test Example

```python
def test_hash_password():
    """Test password hashing."""
    from backend.auth_utils import hash_password, verify_password
    
    password = "testpassword123"
    hash_result = hash_password(password)
    
    assert hash_result is not None
    assert verify_password(password, hash_result) is True
```

#### Integration Test Example

```python
def test_register_user(client, mock_db_connection):
    """Test user registration endpoint."""
    response = client.post("/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword123",
        "username": "newuser"
    })
    
    assert response.status_code in [200, 201]
    data = response.json()
    assert "access_token" in data or "token" in data
```

## Frontend Testing

### Setup

1. Install dependencies (already included in package.json):
```bash
cd frontend
npm install
```

2. Run tests:
```bash
# Run all tests
npm test

# Run tests with coverage
npm run test:ci

# Run tests in watch mode
npm run test:watch
```

### Test Structure

```
frontend/src/
├── __tests__/
│   ├── App.test.jsx
│   └── integration/
│       └── chatFlow.test.jsx
└── components/
    └── features/
        └── __tests__/
            ├── PistaChat.test.jsx
            └── Login.test.jsx
```

### Writing Frontend Tests

#### Component Test Example

```javascript
import { render, screen } from '@testing-library/react';
import Login from '../Login';

test('renders login form', () => {
  render(<Login />);
  const emailInput = screen.getByLabelText(/email/i);
  expect(emailInput).toBeInTheDocument();
});
```

## Pre-commit Hooks

Pre-commit hooks automatically run tests and linting before each commit.

### Setup

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### What Runs Before Commit

1. **File Checks**: Trailing whitespace, end-of-file, YAML/JSON validation
2. **Python Formatting**: Black formatter
3. **Python Linting**: Flake8
4. **JavaScript Linting**: ESLint
5. **Backend Tests**: Unit and integration tests
6. **Frontend Tests**: Component and integration tests

**Note**: If tests fail, the commit will be blocked. Fix issues and try again.

## GitHub Actions CI

CI workflows run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

### Workflows

1. **Backend CI** (`.github/workflows/ci-backend.yml`)
   - Runs Python tests
   - Checks code coverage (minimum 60%)
   - Uploads coverage reports

2. **Frontend CI** (`.github/workflows/ci-frontend.yml`)
   - Runs JavaScript/React tests
   - Checks code coverage (minimum 50%)
   - Builds production bundle

3. **Full CI** (`.github/workflows/ci-full.yml`)
   - Runs both backend and frontend tests
   - Generates combined coverage report

### Coverage Reports

Coverage reports are available:
- In GitHub Actions artifacts
- Uploaded to Codecov (if configured)
- Generated as HTML in `htmlcov/` (backend) and `frontend/coverage/` (frontend)

## Code Coverage Goals

- **Backend**: Minimum 60% coverage
- **Frontend**: Minimum 50% coverage

Coverage is checked in CI and will fail if below thresholds.

## Database Sync

### Manual Sync

Sync local database with production:

```bash
# Full sync of all tables
python scripts/sync_db_production.py --full-sync

# Sync specific tables
python scripts/sync_db_production.py --tables games,users

# Incremental sync (last 7 days)
python scripts/sync_db_production.py --incremental --tables games,users

# Dry run (see what would be synced)
python scripts/sync_db_production.py --dry-run
```

### Scheduled Sync

#### Linux/Mac (Cron)

Add to crontab:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/project/scripts/sync_db_schedule.sh
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 2:00 AM
4. Action: Start a program
5. Program: `powershell.exe`
6. Arguments: `-File "C:\path\to\project\scripts\sync_db_schedule.ps1"`

### Environment Variables

Set these environment variables:

```bash
# Production database (read-only recommended)
export PROD_DATABASE_URL="postgresql://user:pass@prod-host:5432/dbname"

# Local database
export DATABASE_URL="postgresql://user:pass@localhost:5432/pista_local"
```

## Best Practices

1. **Write tests first** (TDD) or alongside code
2. **Keep tests isolated** - each test should be independent
3. **Use fixtures** - reuse common test setup
4. **Mock external services** - don't hit real APIs in tests
5. **Test edge cases** - not just happy paths
6. **Keep tests fast** - unit tests should be < 1 second each
7. **Update tests** - when changing code, update tests too

## Troubleshooting

### Tests failing locally but passing in CI

- Check environment variables
- Ensure test database is set up
- Check Python/Node versions match CI

### Pre-commit hooks not running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Coverage below threshold

- Add more test cases
- Test edge cases and error paths
- Use coverage reports to find untested code

### Database sync fails

- Verify database URLs are correct
- Check network connectivity
- Ensure production database allows connections
- Review logs in `logs/db_sync.log`
