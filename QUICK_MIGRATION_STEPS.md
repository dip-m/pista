# Quick Migration Steps - PostgreSQL + OAuth

## Step 1: Run Migration Script

```bash
# Install dependencies
pip install psycopg2-binary

# Run migration (replace with your PostgreSQL URL)
python update_utils/migrate_to_postgres.py \
  --sqlite-db gen/bgg_semantic.db \
  --postgres-url "postgresql://user:password@host:5432/dbname"
```

## Step 2: Deploy on Render

1. **Create PostgreSQL database** in Render
2. **Create Web Service** and connect repo
3. **Set environment variables** (see render.yaml)
4. **Deploy** - Render will use render.yaml automatically

## Step 3: Deploy Frontend on Netlify

1. Connect GitHub repo to Netlify
2. Set build directory: `frontend`
3. Set build command: `npm run build`
4. Set environment variable: `REACT_APP_API_BASE_URL`

## Step 4: Configure OAuth

Set these in Render environment variables:
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET`
- `META_CLIENT_ID` / `META_CLIENT_SECRET`
- `OAUTH_REDIRECT_BASE` (your Netlify URL)
- `BEARER_TOKEN` (if needed)

## Important Notes

- **Local registration removed** - Only OAuth (Google/Microsoft/Meta) + Email
- **All database queries updated** to support PostgreSQL
- **BEARER_TOKEN** moved to environment variables
- **Migration script** handles user data conversion
