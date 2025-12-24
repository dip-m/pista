# PostgreSQL + OAuth Migration Guide

Complete guide for migrating Pista to PostgreSQL with OAuth authentication.

## Overview

This migration includes:
1. **PostgreSQL Database** - Replace SQLite with PostgreSQL
2. **OAuth Authentication** - Google, Microsoft, Meta + Email only (no local username/password)
3. **Architecture Changes** - Render backend + PostgreSQL + Netlify frontend
4. **Environment Variables** - BEARER_TOKEN moved to env

---

## Step 1: Run Migration Script

### Prerequisites
- PostgreSQL database (local or hosted)
- SQLite database file (`gen/bgg_semantic.db`)

### Run Migration

```bash
# Install PostgreSQL client library
pip install psycopg2-binary

# Run migration
python update_utils/migrate_to_postgres.py \
  --sqlite-db gen/bgg_semantic.db \
  --postgres-url postgresql://user:password@host:5432/database
```

### For Render PostgreSQL

1. **Create PostgreSQL database** in Render dashboard
2. **Get connection string** from Render
3. **Run migration**:
   ```bash
   python update_utils/migrate_to_postgres.py \
     --sqlite-db gen/bgg_semantic.db \
     --postgres-url "postgresql://user:pass@host:5432/dbname"
   ```

---

## Step 2: Configure OAuth Providers

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add redirect URI: `https://your-frontend.netlify.app/auth/callback/google`
4. Get Client ID and Client Secret

### Microsoft OAuth
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register an app
3. Add redirect URI: `https://your-frontend.netlify.app/auth/callback/microsoft`
4. Get Client ID and Client Secret

### Meta (Facebook) OAuth
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create an app
3. Add redirect URI: `https://your-frontend.netlify.app/auth/callback/meta`
4. Get App ID and App Secret

---

## Step 3: Deploy Backend on Render

### Create PostgreSQL Database
1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Name: `pista-db`
3. Plan: Free (or paid)
4. Note the connection string

### Deploy Backend Service
1. **New +** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `pista-backend`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r update_utils/requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. **Set Environment Variables**:
   ```
   DB_TYPE=postgres
   DATABASE_URL=<from PostgreSQL service>
   ALLOWED_ORIGINS=https://your-frontend.netlify.app
   JWT_SECRET_KEY=<generate-random-key>
   ENVIRONMENT=production
   GOOGLE_CLIENT_ID=<your-google-client-id>
   GOOGLE_CLIENT_SECRET=<your-google-client-secret>
   MICROSOFT_CLIENT_ID=<your-microsoft-client-id>
   MICROSOFT_CLIENT_SECRET=<your-microsoft-client-secret>
   META_CLIENT_ID=<your-meta-client-id>
   META_CLIENT_SECRET=<your-meta-client-secret>
   OAUTH_REDIRECT_BASE=https://your-frontend.netlify.app
   BEARER_TOKEN=<your-bearer-token>
   OPENAI_API_KEY=<your-key>
   REPLICATE_API_TOKEN=<your-token>
   ```

5. **Deploy** - Render will automatically use the `render.yaml` configuration

---

## Step 4: Deploy Frontend on Netlify

### Option A: Netlify CLI

```bash
cd frontend

# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Build
npm run build

# Deploy
netlify deploy --prod --dir=build
```

### Option B: Netlify Dashboard

1. Go to [Netlify](https://netlify.com)
2. **"Add new site"** → **"Import an existing project"**
3. Connect your GitHub repository
4. **Build settings**:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/build`

5. **Environment Variables**:
   ```
   REACT_APP_API_BASE_URL=https://your-backend.onrender.com
   ```

6. **Deploy**

---

## Step 5: Update Frontend for OAuth

The frontend needs to be updated to:
1. Remove local registration form
2. Add OAuth login buttons (Google, Microsoft, Meta)
3. Add email login/register
4. Handle OAuth callbacks

---

## API Endpoints Changed

### Removed
- `POST /auth/register` - Local username/password registration
- `POST /auth/login` - Local username/password login

### New
- `POST /auth/oauth/callback` - OAuth callback handler
- `POST /auth/email/register` - Email-based registration
- `POST /auth/email/login` - Email-based login

### OAuth Callback Request
```json
{
  "provider": "google|microsoft|meta",
  "token": "oauth-access-token",
  "email": "user@example.com",
  "name": "User Name"
}
```

---

## Migration Notes

### User Data Migration
- Existing users with `username` are migrated to `email` provider
- Email is set to `username@migrated.local` if username doesn't contain "@"
- Password hashes are preserved
- `is_admin` flag is preserved

### Database Changes
- `users` table now has `email`, `oauth_provider`, `oauth_id` columns
- `username` is optional (can be NULL)
- `password_hash` is optional (only for email provider)
- Unique constraint on `(oauth_provider, oauth_id)`

---

## Testing Checklist

- [ ] Backend connects to PostgreSQL
- [ ] OAuth Google login works
- [ ] OAuth Microsoft login works
- [ ] OAuth Meta login works
- [ ] Email registration works
- [ ] Email login works
- [ ] Frontend connects to backend
- [ ] All existing features work
- [ ] Admin functionality works

---

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` is correct
- Check PostgreSQL is accessible from Render
- Ensure database exists and user has permissions

### OAuth Issues
- Verify redirect URIs match exactly
- Check client IDs and secrets are correct
- Verify OAuth apps are configured correctly

### Migration Issues
- Run migration script with `--batch-size 100` for large tables
- Check PostgreSQL logs for errors
- Verify foreign key constraints are satisfied

---

## Rollback Plan

If issues occur:
1. Keep SQLite database as backup
2. Switch `DB_TYPE=sqlite` in environment
3. Update `DATABASE_URL` to point back to SQLite file path
4. Restart service

