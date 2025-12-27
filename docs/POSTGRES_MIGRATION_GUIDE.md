# PostgreSQL Migration Guide

Complete guide to switch from SQLite to PostgreSQL while preserving all features and functionalities.

## Prerequisites

1. **PostgreSQL Database** - You need a PostgreSQL database instance:
   - **Local**: Install PostgreSQL locally
   - **Cloud**: Use Render, Railway, AWS RDS, or any PostgreSQL hosting service
   - **Connection String**: Format: `postgresql://user:password@host:5432/database`

2. **Python Dependencies**:
   ```bash
   pip install psycopg2-binary
   ```

## Step 1: Set Up PostgreSQL Database

### Option A: Local PostgreSQL

1. **Install PostgreSQL** (if not already installed):
   - Windows: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
   - macOS: `brew install postgresql`
   - Linux: `sudo apt-get install postgresql` (Ubuntu/Debian)

2. **Create Database**:
   ```bash
   # Connect to PostgreSQL
   psql -U postgres
   
   # Create database
   CREATE DATABASE pista;
   
   # Create user (optional)
   CREATE USER pista_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE pista TO pista_user;
   ```

3. **Connection String**:
   ```
   postgresql://pista_user:your_password@localhost:5432/pista
   ```

### Option B: Render PostgreSQL (Recommended for Production)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `pista-db`
   - **Database**: `pista`
   - **User**: `pista_user`
   - **Plan**: Free (or paid for better performance)
4. Copy the **Internal Database URL** (for Render services) or **External Database URL** (for local migration)

## Step 2: Run Migration Script

### Backup Your SQLite Database First!

```bash
# Create backup
cp gen/bgg_semantic.db gen/bgg_semantic.db.backup
```

### Run Migration

```bash
# For local PostgreSQL
python update_utils/migrate_to_postgres.py \
  --sqlite-db gen/bgg_semantic.db \
  --postgres-url postgresql://pista_user:password@localhost:5432/pista

# For Render PostgreSQL (use External Database URL)
python update_utils/migrate_to_postgres.py \
  --sqlite-db gen/bgg_semantic.db \
  --postgres-url "postgresql://pista_user:password@dpg-xxxxx-a.oregon-postgres.render.com/pista"
```

### Migration Process

The script will:
1. ✅ Create PostgreSQL schema (tables, indexes, constraints)
2. ✅ Migrate all game data (games, mechanics, categories, etc.)
3. ✅ Migrate user data (converting to OAuth schema if needed)
4. ✅ Migrate user collections, chat threads, messages
5. ✅ Migrate feature mods, feedback, A/B test configs
6. ✅ Preserve all relationships and foreign keys

**Expected Output**:
```
Connecting to SQLite database...
Connecting to PostgreSQL database...
Ensuring PostgreSQL schema exists...
Schema ensured
Migrating table: games
  Migrating 50000 rows...
  Migrated 1000/50000 rows
  ...
Migration completed successfully!
```

## Step 3: Update Environment Variables

### Create/Update `.env` File

Create a `.env` file in the project root (or update existing):

```env
# Database Configuration
DB_TYPE=postgres
DATABASE_URL=postgresql://pista_user:password@localhost:5432/pista

# For Render (use Internal Database URL)
# DATABASE_URL=postgresql://pista_user:password@dpg-xxxxx-a.oregon-postgres.render.com/pista

# Other configurations (keep existing values)
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000

# Security
JWT_SECRET_KEY=your-secret-key-here
BEARER_TOKEN=your-bearer-token-here

# OAuth (if configured)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
META_CLIENT_ID=your-meta-client-id
META_CLIENT_SECRET=your-meta-client-secret
OAUTH_REDIRECT_BASE=http://localhost:3000

# API Keys
OPENAI_API_KEY=your-openai-key
REPLICATE_API_TOKEN=your-replicate-token
```

### For Production (Render)

In Render dashboard, set these environment variables:
- `DB_TYPE=postgres`
- `DATABASE_URL` (automatically set from linked database)
- All other environment variables as needed

## Step 4: Verify Migration

### Test Connection

```bash
# Run verification script
python update_utils/verify_postgres.py --postgres-url postgresql://user:pass@host:5432/db
```

Or manually test:

```python
import psycopg2

conn = psycopg2.connect("postgresql://user:pass@host:5432/db")
cur = conn.cursor()

# Check tables
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
tables = cur.fetchall()
print("Tables:", [t[0] for t in tables])

# Check users
cur.execute("SELECT COUNT(*) FROM users")
user_count = cur.fetchone()[0]
print(f"Users: {user_count}")

# Check games
cur.execute("SELECT COUNT(*) FROM games")
game_count = cur.fetchone()[0]
print(f"Games: {game_count}")

conn.close()
```

### Start Backend Server

```bash
# The server will automatically use PostgreSQL if DB_TYPE=postgres
python main.py
# or
uvicorn main:app --reload
```

Check logs for:
```
Connecting to PostgreSQL database...
PostgreSQL schema ensured
```

## Step 5: Test All Features

After migration, test these features to ensure everything works:

- ✅ **User Registration/Login** (Email, Google, Microsoft, Meta)
- ✅ **Game Search** and filtering
- ✅ **User Collections** (add/remove games)
- ✅ **Chat/Conversations** (create threads, send messages)
- ✅ **Feature Modifications** (add/remove mechanics, categories, etc.)
- ✅ **Feedback System** (submit feedback)
- ✅ **A/B Testing** (if configured)
- ✅ **Admin Features** (if you have admin users)

## Troubleshooting

### Connection Errors

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
- Check PostgreSQL is running: `pg_isready` or check service status
- Verify connection string format
- Check firewall/network settings
- For Render: Use Internal Database URL for services on Render, External URL for local access

### Migration Errors

**Error**: `relation "users" already exists`

**Solution**: The schema already exists. The migration will skip existing data with `ON CONFLICT DO NOTHING`.

**Error**: `column "email" does not exist`

**Solution**: Make sure you're using the latest `schema_postgres.sql` which includes OAuth columns.

### Data Issues

**Missing Data**: Check migration logs for any tables that failed. Re-run migration for specific tables if needed.

**Foreign Key Violations**: Ensure tables are migrated in the correct order (games first, then relationships).

## Rollback Plan

If you need to rollback to SQLite:

1. **Stop the backend server**
2. **Update `.env`**:
   ```env
   DB_TYPE=sqlite
   DB_PATH=./gen/bgg_semantic.db
   ```
3. **Remove `DATABASE_URL`** from environment variables
4. **Restart server** - it will use SQLite again

Your SQLite database file (`gen/bgg_semantic.db`) remains unchanged, so you can always switch back.

## Next Steps

After successful migration:

1. ✅ **Deploy to Production**: Use Render PostgreSQL for production
2. ✅ **Update Frontend**: Ensure frontend points to new backend URL
3. ✅ **Monitor Performance**: PostgreSQL should handle larger datasets better
4. ✅ **Backup Strategy**: Set up regular PostgreSQL backups

## Support

If you encounter issues:
1. Check migration logs for specific errors
2. Verify PostgreSQL connection string
3. Ensure all dependencies are installed (`psycopg2-binary`)
4. Check PostgreSQL server logs

---

**Migration Complete!** 🎉

Your application is now running on PostgreSQL with all features preserved.
