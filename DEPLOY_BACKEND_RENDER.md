# Deploying Pista Backend on Render

This guide walks you through deploying the Pista backend service on Render's free tier.

## Prerequisites

1. A [Render account](https://render.com) (free tier available)
2. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)
3. Your Supabase PostgreSQL database URL (already configured)
4. All required environment variables

## Step-by-Step Deployment

### Option 1: Using render.yaml (Recommended - Automated)

If your `render.yaml` file is in the repository root, Render will auto-detect it.

#### Steps:

1. **Sign up/Login to Render**
   - Go to [render.com](https://render.com)
   - Sign up or log in with your GitHub/GitLab/Bitbucket account

2. **Create New Web Service**
   - Click "New +" → "Blueprint"
   - Connect your Git repository
   - Render will detect `render.yaml` automatically
   - Click "Apply"

3. **Review Configuration**
   - Render will create the service based on `render.yaml`
   - Verify the settings match:
     - **Name**: `pista-backend`
     - **Environment**: `Python`
     - **Build Command**: `pip install -r update_utils/requirements.txt`
     - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

4. **Set Environment Variables**
   - Go to your service → "Environment" tab
   - Add the following variables (click "Add Environment Variable" for each):

   **Required Variables:**
   ```
   ALLOWED_ORIGINS=https://your-frontend-domain.netlify.app,http://localhost:3000
   DB_TYPE=postgres
   DATABASE_URL=postgresql://postgres.azejopggiscyfjyaiosi:Pista_01123@aws-1-eu-west-1.pooler.supabase.com:5432/postgres
   ENVIRONMENT=production
   JWT_SECRET_KEY=<generate-a-strong-random-secret-key>
   OAUTH_REDIRECT_BASE=https://your-frontend-domain.netlify.app
   ```

   **Optional (if using OAuth):**
   ```
   GOOGLE_CLIENT_ID=<your-google-client-id>
   GOOGLE_CLIENT_SECRET=<your-google-client-secret>
   MICROSOFT_CLIENT_ID=<your-microsoft-client-id>
   MICROSOFT_CLIENT_SECRET=<your-microsoft-client-secret>
   META_CLIENT_ID=<your-meta-client-id>
   META_CLIENT_SECRET=<your-meta-client-secret>
   ```

   **Optional (if using AI features):**
   ```
   OPENAI_API_KEY=<your-openai-api-key>
   REPLICATE_API_TOKEN=<your-replicate-token>
   BEARER_TOKEN=<your-bearer-token>
   ```

5. **Deploy**
   - Click "Save Changes"
   - Render will automatically start building and deploying
   - Monitor the build logs in the "Logs" tab

6. **Get Your Backend URL**
   - Once deployed, you'll get a URL like: `https://pista-backend.onrender.com`
   - Use this URL in your frontend's `REACT_APP_API_BASE_URL`

---

### Option 2: Manual Setup (Without render.yaml)

If you prefer to set up manually or `render.yaml` isn't detected:

1. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your Git repository
   - Select the repository and branch

2. **Configure Service Settings**
   - **Name**: `pista-backend` (or your preferred name)
   - **Environment**: `Python 3`
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (or `./` if needed)
   - **Build Command**: 
     ```bash
     pip install -r update_utils/requirements.txt
     ```
   - **Start Command**: 
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```

3. **Set Environment Variables**
   - Same as Option 1, Step 4 above

4. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy automatically

---

## Important Notes

### Free Tier Limitations

- **Spinning Down**: Free tier services spin down after 15 minutes of inactivity
- **Cold Start**: First request after spin-down may take 30-60 seconds
- **Bandwidth**: 100GB/month included
- **Build Time**: 500 build minutes/month

### Database

- Your PostgreSQL database is already hosted on Supabase
- No need to create a Render PostgreSQL service
- Make sure your Supabase database allows connections from Render's IPs

### Port Configuration

- Render automatically sets the `$PORT` environment variable
- Your start command uses `--port $PORT` to bind to the correct port
- **Do not hardcode port 8000** in production

### CORS Configuration

- Set `ALLOWED_ORIGINS` to include:
  - Your production frontend URL
  - Your localhost for development (optional)
  - Separate multiple origins with commas: `https://app1.com,https://app2.com`

### Health Check

- Render automatically checks if your service is responding
- Your FastAPI app should have a health endpoint (if not, add one)
- Example health endpoint:
  ```python
  @app.get("/health")
  def health():
      return {"status": "ok"}
  ```

---

## Post-Deployment Checklist

- [ ] Service is running and accessible
- [ ] Environment variables are set correctly
- [ ] Database connection is working
- [ ] CORS is configured for your frontend domain
- [ ] Test API endpoints are responding
- [ ] Frontend is configured with the new backend URL
- [ ] OAuth redirect URLs are updated in OAuth provider settings

---

## Troubleshooting

### Build Fails

1. **Check build logs** in Render dashboard
2. **Verify requirements.txt** is in `update_utils/` directory
3. **Check Python version** - ensure it matches `runtime.txt` (Python 3.11)

### Service Won't Start

1. **Check start command** - must use `$PORT` variable
2. **Verify imports** - ensure all Python imports are available
3. **Check database connection** - verify `DATABASE_URL` is correct
4. **Review logs** - check for error messages

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
   curl -H "Origin: https://your-frontend.com" https://your-backend.onrender.com/health
   ```

---

## Updating Your Deployment

1. **Push changes** to your Git repository
2. **Render auto-deploys** on push to the main branch
3. **Monitor deployment** in the Render dashboard
4. **Check logs** if deployment fails

---

## Cost Considerations

### Free Tier
- ✅ Free for low-traffic applications
- ✅ Automatic HTTPS
- ✅ Custom domains
- ⚠️ Spins down after inactivity
- ⚠️ Limited build minutes

### Paid Tier ($7/month)
- ✅ Always-on (no spin-down)
- ✅ More build minutes
- ✅ Better performance
- ✅ Priority support

---

## Next Steps

After backend is deployed:

1. **Update frontend** with backend URL:
   ```
   REACT_APP_API_BASE_URL=https://pista-backend.onrender.com
   ```

2. **Update OAuth redirect URIs** in:
   - Google Cloud Console
   - Microsoft Azure Portal
   - Meta Developer Portal

3. **Test the integration**:
   - Test authentication
   - Test API endpoints
   - Test chat functionality

---

## Support

- Render Documentation: https://render.com/docs
- Render Community: https://community.render.com
- Check service logs in Render dashboard for debugging
