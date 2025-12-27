# PostgreSQL Switch - Quick Summary

## What Was Done

✅ **Migration Script Updated** - Now handles both old and new OAuth schema automatically
✅ **Verification Script Created** - Test PostgreSQL connection and schema
✅ **Migration Guide Created** - Complete step-by-step instructions
✅ **Quick Switch Scripts** - Bash and PowerShell scripts for easy migration

## Quick Start

### 1. Set Up PostgreSQL Database

**Option A: Local PostgreSQL**
```bash
# Create database
psql -U postgres
CREATE DATABASE pista;
```

**Option B: Render PostgreSQL (Recommended)**
- Go to Render Dashboard → New PostgreSQL
- Copy connection string

### 2. Run Migration

**Windows (PowerShell):**
```powershell
.\update_utils\switch_to_postgres.ps1 -PostgresUrl "postgresql://user:pass@host:5432/pista"
```

**Linux/Mac (Bash):**
```bash
chmod +x update_utils/switch_to_postgres.sh
./update_utils/switch_to_postgres.sh postgresql://user:pass@host:5432/pista
```

**Manual:**
```bash
python update_utils/migrate_to_postgres.py \
  --sqlite-db gen/bgg_semantic.db \
  --postgres-url postgresql://user:pass@host:5432/pista
```

### 3. Update Environment Variables

Create/update `.env` file:
```env
DB_TYPE=postgres
DATABASE_URL=postgresql://user:pass@host:5432/pista
```

### 4. Verify & Test

```bash
# Verify connection
python update_utils/verify_postgres.py --postgres-url postgresql://user:pass@host:5432/pista

# Start server (will use PostgreSQL automatically)
python main.py
```

## Features Preserved

✅ All game data (games, mechanics, categories, etc.)
✅ All user data (with OAuth schema conversion)
✅ User collections
✅ Chat threads and messages
✅ Feature modifications
✅ Feedback system
✅ A/B test configurations
✅ All relationships and foreign keys

## Files Created/Updated

- `POSTGRES_MIGRATION_GUIDE.md` - Complete migration guide
- `update_utils/verify_postgres.py` - Verification script
- `update_utils/switch_to_postgres.sh` - Bash quick switch script
- `update_utils/switch_to_postgres.ps1` - PowerShell quick switch script
- `update_utils/migrate_to_postgres.py` - Updated to handle OAuth schema

## Rollback

To switch back to SQLite:
```env
DB_TYPE=sqlite
DB_PATH=./gen/bgg_semantic.db
# Remove DATABASE_URL
```

Your SQLite database remains unchanged as a backup.

## Next Steps

1. ✅ Run migration script
2. ✅ Update `.env` file
3. ✅ Verify connection
4. ✅ Test all features
5. ✅ Deploy to production (if ready)

---

**Ready to switch?** Follow the steps above or see `POSTGRES_MIGRATION_GUIDE.md` for detailed instructions.
