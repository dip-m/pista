# Supabase PostgreSQL Setup Guide

Complete guide for using Supabase PostgreSQL database for both local development and Render deployment.

## Overview

This setup uses **Supabase PostgreSQL** as the shared database for:
- ✅ Local development
- ✅ Render production deployment
- ✅ Single source of truth for all data

## Connection String

Your Supabase connection string:
```
postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres
```

## Step 1: Local Development Setup

### Update Local `.env` File

Create or update `.env` in your project root:

```env
# Database Configuration - Supabase
DB_TYPE=postgres
DATABASE_URL=postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres

# Other configurations
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

### Test Local Connection

```bash
# Verify connection
python update_utils/verify_postgres.py --postgres-url "postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres"

# Start local server
python main.py
```

You should see: `Connecting to PostgreSQL database...`

## Step 2: Migrate Data to Supabase

### Run Migration Script

**Windows PowerShell:**
```powershell
.\update_utils\switch_to_postgres.ps1 -PostgresUrl "postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres"
```

**Linux/Mac:**
```bash
chmod +x update_utils/switch_to_postgres.sh
./update_utils/switch_to_postgres.sh "postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres"
```

**Or manually:**
```bash
python update_utils/migrate_to_postgres.py \
  --sqlite-db gen/bgg_semantic.db \
  --postgres-url "postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres"
```

The migration will:
1. ✅ Create all tables in Supabase
2. ✅ Migrate all game data
3. ✅ Migrate all user data (with OAuth schema conversion)
4. ✅ Migrate collections, chat threads, messages
5. ✅ Migrate all other data

## Step 3: Configure Render Deployment

### Update Render Environment Variables

1. Go to **Render Dashboard** → Your Web Service
2. Go to **"Environment"** tab
3. Set these environment variables:

```
DB_TYPE=postgres
DATABASE_URL=postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres
```

**Important**: 
- The `render.yaml` has been updated to use `sync: false` for `DATABASE_URL`
- You need to manually set `DATABASE_URL` in Render dashboard with the Supabase connection string

### Other Environment Variables

Set these in Render dashboard as well:
- `ALLOWED_ORIGINS` - Your frontend URL
- `JWT_SECRET_KEY` - Auto-generated or set manually
- `ENVIRONMENT=production`
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET`
- `META_CLIENT_ID` / `META_CLIENT_SECRET`
- `OAUTH_REDIRECT_BASE` - Your frontend URL
- `BEARER_TOKEN`
- `OPENAI_API_KEY`
- `REPLICATE_API_TOKEN`

## Step 4: Verify Both Environments

### Verify Local Connection

```bash
python update_utils/verify_postgres.py --postgres-url "postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres"
```

### Verify Render Connection

1. Go to Render dashboard → Your Web Service
2. Check **"Logs"** tab
3. Look for: `Connecting to PostgreSQL database...` and `PostgreSQL schema ensured`

### Test Data Sync

1. **Create a test user locally** (via your local backend)
2. **Check Supabase dashboard** - the user should appear
3. **Access from Render** - the same user should be visible

## Supabase Dashboard Access

You can also manage your database through Supabase dashboard:

1. Go to [Supabase Dashboard](https://app.supabase.com/)
2. Select your project
3. Go to **"Database"** → **"Tables"** to view data
4. Go to **"SQL Editor"** to run queries
5. Go to **"Settings"** → **"Database"** for connection info

## Security Best Practices

### 1. Connection String Security

- ✅ Never commit connection strings to git
- ✅ Use environment variables only
- ✅ Rotate password regularly in Supabase dashboard

### 2. Supabase Security Features

- **Row Level Security (RLS)**: Consider enabling for sensitive tables
- **Connection Pooling**: Supabase provides connection pooling
- **SSL**: Connection string uses SSL by default

### 3. Environment-Specific Configuration

**Local Development**:
```env
OAUTH_REDIRECT_BASE=http://localhost:3000
```

**Production (Render)**:
```env
OAUTH_REDIRECT_BASE=https://your-frontend.netlify.app
```

## Troubleshooting

### DNS Resolution Error

**Issue**: `could not translate host name "db.azejopggiscyfjyaiosi.supabase.co" to address`

**Solutions**:
1. ✅ **Verify connection string in Supabase dashboard**:
   - Go to Supabase Dashboard → Your Project → Settings → Database
   - Copy the connection string from there (it might be slightly different)
   - Check if there's a "Connection Pooling" URL vs "Direct Connection" URL
2. ✅ **Check internet connection** - Try accessing Supabase dashboard in browser
3. ✅ **Try from different network** - May be firewall/DNS issue
4. ✅ **Verify Supabase project is active** - Check project status in dashboard
5. ✅ **Use Connection Pooling URL** - Supabase provides a pooling URL that might work better

### Connection Timeout

**Issue**: Can't connect to Supabase from local machine or Render

**Solutions**:
1. ✅ Verify connection string is correct (get fresh copy from Supabase dashboard)
2. ✅ Check Supabase project is active (not paused)
3. ✅ Verify network/firewall settings
4. ✅ Check Supabase dashboard for connection limits
5. ✅ Ensure IP is not blocked (Supabase may have IP restrictions)
6. ✅ Try using Supabase's connection pooling URL instead

### Migration Errors

**Issue**: Migration fails with connection or permission errors

**Solutions**:
1. ✅ Verify connection string credentials
2. ✅ Check Supabase database is accessible
3. ✅ Ensure user has proper permissions
4. ✅ Check Supabase logs in dashboard

### Render Can't Connect

**Issue**: Render service shows database connection errors

**Solutions**:
1. ✅ Verify `DATABASE_URL` is set correctly in Render dashboard
2. ✅ Check `DB_TYPE=postgres` is set
3. ✅ Verify Supabase project is active
4. ✅ Check Render logs for specific error messages

## Benefits of Supabase

✅ **Free Tier Available**: Generous free tier for development  
✅ **Automatic Backups**: Built-in backup system  
✅ **Real-time Features**: Can enable real-time subscriptions if needed  
✅ **Dashboard Access**: Easy database management via web UI  
✅ **Connection Pooling**: Built-in connection pooling  
✅ **SSL by Default**: Secure connections  
✅ **Scalable**: Easy to upgrade as needed  

## Next Steps

1. ✅ Update local `.env` with Supabase connection string
2. ✅ Run migration script to migrate data
3. ✅ Verify local connection works
4. ✅ Set `DATABASE_URL` in Render dashboard
5. ✅ Deploy to Render
6. ✅ Verify both environments work

---

**Your local and Render deployment will now share the same Supabase PostgreSQL database!** 🎉
