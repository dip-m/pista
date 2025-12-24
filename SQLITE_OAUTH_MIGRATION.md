# SQLite OAuth Migration Guide

## Issue
When registering with email, you get: `sqlite3.OperationalError: no such column: email`

This happens because your existing SQLite database has the old schema without OAuth columns.

## Solution
The migration code has been updated to automatically add the required columns. You need to **restart your backend server** to trigger the migration.

## What the Migration Does

1. **Checks for missing columns**: `email`, `oauth_provider`, `oauth_id`
2. **If missing, creates new table** with OAuth-compatible schema:
   - `email` (TEXT, UNIQUE)
   - `username` (TEXT, optional)
   - `oauth_provider` (TEXT) - 'google', 'microsoft', 'meta', or 'email'
   - `oauth_id` (TEXT) - OAuth provider user ID
   - `password_hash` (TEXT, optional - only for email auth)
   - `bgg_id` (TEXT)
   - `is_admin` (INTEGER)
   - `created_at` (TIMESTAMP)

3. **Migrates existing users**:
   - Converts old username-based users to email-based
   - Sets `email` = `username@migrated.local` (if username doesn't contain @)
   - Sets `oauth_provider` = 'email'
   - Preserves `password_hash`, `bgg_id`, `is_admin`

4. **Creates indexes**:
   - Unique index on `email`
   - Unique index on `(oauth_provider, oauth_id)` for OAuth users

## Steps to Fix

1. **Stop your backend server** (if running)

2. **Restart the backend server**:
   ```bash
   # The migration will run automatically on startup
   python main.py
   # or
   uvicorn main:app --reload
   ```

3. **Check the logs** - You should see:
   ```
   Migrating users table to OAuth-compatible schema
   Migrating existing users to email-based auth
   OAuth migration complete
   ```

4. **Try registering again** - Email registration should now work

## Verification

After migration, you can verify the schema:
```python
import sqlite3
conn = sqlite3.connect('gen/bgg_semantic.db')
cur = conn.execute("PRAGMA table_info(users)")
for row in cur.fetchall():
    print(row[1], row[2])  # column name, type
```

You should see:
- `email`
- `oauth_provider`
- `oauth_id`
- `username`
- `password_hash`
- `bgg_id`
- `is_admin`
- `created_at`

## Notes

- **Existing users**: Will be migrated to email provider automatically
- **No data loss**: All user data is preserved
- **Idempotent**: Safe to run multiple times
- **Backup recommended**: Back up your database before migration (just in case)

## Troubleshooting

If migration fails:
1. Check the logs for specific error messages
2. Ensure the database file is writable
3. Make sure no other process has the database locked
4. Try backing up and recreating the database if needed
