# Deploying Pista Backend on Railway

Railway offers a more generous free tier ($5/month credit) and no /tmp storage limits, making it ideal for ML workloads.

## Prerequisites

1. A [Railway account](https://railway.app) (free tier: $5/month credit)
2. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)
3. Your Supabase PostgreSQL database URL
4. All required environment variables

## Step-by-Step Deployment

### 1. Sign Up/Login to Railway

- Go to [railway.app](https://railway.app)
- Sign up or log in with your GitHub/GitLab/Bitbucket account

### 2. Create New Project

1. Click "New Project"
2. Select "Deploy from GitHub repo" (or GitLab/Bitbucket)
3. Select your repository
4. Railway will auto-detect the `railway.json` configuration

### 3. Configure Service

**CRITICAL:** Railway may detect both frontend (React) and backend (Python). To ensure it builds only the backend:

1. **In Railway Dashboard:**
   - Go to your service → "Settings" → "Build & Deploy"
   - **Service Type**: Select "Python" (or let it auto-detect from `nixpacks.toml`)
   - **Build Command**: `pip install --no-cache-dir -r requirements-deploy.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory**: Leave empty (or set to `.`)

2. **If Railway still tries to build frontend/React:**
   - The `nixpacks.toml` file forces Python-only build (should be auto-detected)
   - The `.railwayignore` file excludes `frontend/` and `src/` directories
   - The root `src/` directory has been renamed to `src_old_backup/` to prevent Railway from detecting React
   - If you still see "Error reading src/App.jsx", manually select "Python" as the service type in Railway settings

### 4. Upload FAISS Index Files (Required for Similarity Search)

The FAISS index files (`game_vectors.index` and `game_ids.json`) are required for similarity search functionality. The server will start without them, but similarity search won't work.

**Generate the Index Files Locally:**

First, generate the index files on your local machine:
```bash
python update_utils/export_faiss.py \
  --db gen/bgg_semantic.db \
  --index-out gen/game_vectors.index \
  --id-map-out gen/game_ids.json
```

**Option A: Include in Git Repository (Simplest)**

If the index files are reasonable size (< 100MB), commit them to Git:
```bash
git add gen/game_vectors.index gen/game_ids.json
git commit -m "Add FAISS index files for deployment"
git push
```
Railway will automatically include them in the deployment.

**Option B: Upload via Railway CLI (For Large Files)**

1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Link your project: `railway link`
4. Upload files:
   ```bash
   railway run --service <your-service-name> -- mkdir -p /app/gen
   railway run --service <your-service-name> -- cp gen/game_vectors.index /app/gen/
   railway run --service <your-service-name> -- cp gen/game_ids.json /app/gen/
   ```

**Option C: Use Railway Persistent Volume**

1. In Railway dashboard → Your service → "Volumes" tab
2. Create a volume named `gen` mounted at `/app/gen`
3. Upload files using Railway CLI or SSH into the service

**Note:** The server will log a warning if the index files are missing, but it will still start. Similarity search features will be disabled until the files are uploaded. Check the `/health` endpoint - it will show `"engine": "not_loaded"` if the index is missing.

### 5. Set Environment Variables

Go to your service → "Variables" tab → "Raw Editor" and add:

```env
# Database
DB_TYPE=postgres
DATABASE_URL=postgresql://postgres.azejopggiscyfjyaiosi:Pista_01123@aws-1-eu-west-1.pooler.supabase.com:5432/postgres

# Environment
ENVIRONMENT=production

# CORS (replace with your frontend URL - include both production and localhost for testing)
ALLOWED_ORIGINS=https://pistatabletop.netlify.app,http://localhost:3000

# JWT (Railway will generate this, or set manually)
JWT_SECRET_KEY=<generate-a-strong-random-secret-key>

# OAuth Redirect Base (your frontend URL)
OAUTH_REDIRECT_BASE=https://your-frontend-domain.netlify.app

# OAuth Credentials (if using)
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
MICROSOFT_CLIENT_ID=<your-microsoft-client-id>
MICROSOFT_CLIENT_SECRET=<your-microsoft-client-secret>
META_CLIENT_ID=<your-meta-client-id>
META_CLIENT_SECRET=<your-meta-client-secret>

# API Keys (if using)
OPENAI_API_KEY=<your-openai-api-key>
REPLICATE_API_TOKEN=<your-replicate-token>
BEARER_TOKEN=<your-bearer-token>
```

### 5. Deploy

1. Click "Deploy" or push to your main branch
2. Railway will automatically build and deploy
3. Monitor the build logs in the "Deployments" tab

### 6. Get Your Backend URL

- Once deployed, Railway provides a URL like: `https://pista-backend-production.up.railway.app`
- You can also set a custom domain in "Settings" → "Domains"
- Use this URL in your frontend's `REACT_APP_API_BASE_URL`

## Railway vs Render

### Advantages of Railway:
- ✅ **No /tmp limits** - Better for ML workloads
- ✅ **$5/month free credit** - More generous than Render's free tier
- ✅ **Always-on option** - No forced spin-down
- ✅ **Better build environment** - More resources
- ✅ **Easier configuration** - Simple JSON config

### Free Tier Details:
- $5/month credit (usually enough for small apps)
- 500 hours/month free
- No forced spin-down (unlike Render free tier)
- More build minutes
- Better for ML/MLOps workloads

## Post-Deployment Checklist

- [ ] Service is running and accessible
- [ ] Environment variables are set correctly
- [ ] Database connection is working
- [ ] FAISS index files are uploaded (`game_vectors.index` and `game_ids.json`)
- [ ] Health endpoint shows `"engine": "loaded"` (check `/health` endpoint)
- [ ] CORS is configured for your frontend domain
- [ ] Test API endpoints are responding
- [ ] Frontend is configured with the new backend URL
- [ ] OAuth redirect URLs are updated in OAuth provider settings

## Troubleshooting

### Build Fails

1. **Check build logs** in Railway dashboard
2. **Verify requirements-deploy.txt** exists and is correct
3. **Check Python version** - Railway auto-detects, but you can specify in `runtime.txt`

### Service Won't Start

1. **Check start command** - must use `$PORT` variable
2. **Verify imports** - ensure all Python imports are available
3. **Check database connection** - verify `DATABASE_URL` is correct
4. **Review logs** - check for error messages in Railway dashboard

### Database Connection Issues

1. **Verify DATABASE_URL** format:
   ```
   postgresql://user:password@host:port/database
   ```
2. **Check Supabase connection settings**:
   - Ensure connection pooling is enabled
   - Check if IP restrictions are set
3. **Test connection locally** with the same URL

### CORS Errors

1. **Verify ALLOWED_ORIGINS** includes your frontend URL
2. **Check for trailing slashes** - ensure URLs match exactly
3. **Test with curl**:
   ```bash
   curl -H "Origin: https://your-frontend.com" https://your-backend.railway.app/health
   ```

## Updating Your Deployment

1. **Push changes** to your Git repository
2. **Railway auto-deploys** on push to the main branch
3. **Monitor deployment** in the Railway dashboard
4. **Check logs** if deployment fails

## Cost Management

### Free Tier Usage:
- Monitor usage in Railway dashboard
- $5/month credit is usually enough for:
  - Small to medium traffic
  - Development/testing
  - Personal projects

### If You Exceed Free Tier:
- Railway charges per usage
- Typically $5-10/month for small apps
- Still very affordable
- Much better than Render's limitations

## Next Steps

After backend is deployed:

1. **Update frontend** with backend URL:
   ```
   REACT_APP_API_BASE_URL=https://pista-backend-production.up.railway.app
   ```

2. **Update OAuth redirect URIs** in:
   - Google Cloud Console
   - Microsoft Azure Portal
   - Meta Developer Portal

3. **Test the integration**:
   - Test authentication
   - Test API endpoints
   - Test chat functionality

## Support

- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Check service logs in Railway dashboard for debugging

