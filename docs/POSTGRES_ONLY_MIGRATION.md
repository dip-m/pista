# PostgreSQL-Only Migration Plan

This document tracks the migration from SQLite/PostgreSQL dual support to PostgreSQL-only.

## Status: IN PROGRESS

### Completed
- ✅ Updated `backend/db.py` to PostgreSQL-only
- ✅ Updated `backend/config.py` to require DATABASE_URL

### In Progress
- 🔄 Removing SQLite references from `backend/main.py`
- 🔄 Updating test configuration to use PostgreSQL

### Remaining
- ⏳ Update all query placeholders from `?` to `%s` in main.py
- ⏳ Remove all `DB_TYPE` checks
- ⏳ Update test fixtures to use PostgreSQL
- ⏳ Create comprehensive feature tests
- ⏳ Add account deletion endpoints
- ⏳ Add data export functionality
- ⏳ Update frontend for account deletion

## Key Changes

### Database Connection
- All connections now use PostgreSQL connection pool
- No SQLite fallback code
- `DATABASE_URL` is required (no default)

### Query Syntax
- All queries use `%s` placeholders (PostgreSQL)
- Removed `?` placeholder conversion logic
- All `ON CONFLICT` clauses use PostgreSQL syntax

### Tests
- Tests use PostgreSQL test database
- Test fixtures create/cleanup PostgreSQL database
- No SQLite test database
