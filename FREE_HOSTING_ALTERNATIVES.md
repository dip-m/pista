# Free Backend Hosting Alternatives for Pista

Since Render's free tier has a 2GB /tmp limit that's being exceeded by ML model downloads, here are alternative free hosting options:

## Option 1: Railway (Recommended)

**Free Tier:**
- $5/month credit (enough for small apps)
- 500 hours/month free
- No /tmp limits
- Automatic HTTPS
- PostgreSQL available

**Setup:**
1. Sign up at [railway.app](https://railway.app)
2. Connect GitHub repo
3. Railway auto-detects Python
4. Set environment variables
5. Deploy

**Pros:**
- More generous free tier
- Better for ML workloads
- Easy deployment
- Good documentation

**Cons:**
- Credit-based (but $5/month is usually enough for small apps)

---

## Option 2: Fly.io

**Free Tier:**
- 3 shared-cpu VMs
- 3GB persistent volume per VM
- 160GB outbound data transfer
- No /tmp limits

**Setup:**
1. Sign up at [fly.io](https://fly.io)
2. Install flyctl CLI
3. Run `fly launch` in your project
4. Set environment variables
5. Deploy with `fly deploy`

**Pros:**
- Generous free tier
- Good for ML workloads
- Global edge network
- Persistent storage

**Cons:**
- Requires CLI setup
- Slightly more complex than Render

---

## Option 3: Render (Optimized)

**Current Issue:** 2GB /tmp limit

**Solutions:**
1. **Use deployment-only requirements** (see `requirements-deploy.txt`)
   - Excludes `sentence-transformers`, `ultralytics`, etc.
   - These are only needed for embedding generation, not runtime

2. **Upgrade to paid tier** ($7/month)
   - No /tmp limits
   - Always-on (no spin-down)
   - More resources

---

## Option 4: Google Cloud Run (Free Tier)

**Free Tier:**
- 2 million requests/month
- 360,000 GB-seconds compute
- 180,000 vCPU-seconds
- No /tmp limits

**Setup:**
1. Create Google Cloud account
2. Enable Cloud Run API
3. Build Docker image
4. Deploy to Cloud Run

**Pros:**
- Very generous free tier
- Pay-per-use after free tier
- Scalable
- Good for ML workloads

**Cons:**
- More setup required
- Docker knowledge needed
- Cold starts possible

---

## Option 5: Heroku (Eco Dyno)

**Free Tier:**
- No longer available (discontinued free tier)
- Eco dynos: $5/month
- 550-1000 free dyno hours/month

**Note:** Heroku discontinued free tier, but eco dynos are affordable.

---

## Option 6: PythonAnywhere

**Free Tier:**
- Limited to Python 3.8
- 512MB disk space
- Web apps only
- Limited CPU time

**Pros:**
- Simple setup
- Good for learning

**Cons:**
- Very limited free tier
- May not work for ML workloads
- Python version restrictions

---

## Recommended Solution: Optimize for Render

Since you're already on Render, the best immediate solution is to:

1. **Use `requirements-deploy.txt`** (already created)
   - Removes heavy dependencies not needed at runtime
   - `sentence-transformers` is only used for embedding generation
   - Your app uses pre-computed FAISS embeddings

2. **If that doesn't work, try Railway:**
   - More generous free tier
   - Better for ML workloads
   - Easy migration from Render

---

## Migration Steps (if switching to Railway)

1. Create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. Set environment variables in Railway dashboard
3. Connect GitHub repo
4. Deploy

---

## Quick Fix for Render (Try This First)

The `requirements-deploy.txt` file I created excludes:
- `sentence-transformers` (only needed for embedding scripts)
- `ultralytics` (only if you use image detection)
- `opencv-python` (only if you use image processing)
- `pytesseract` (only if you use OCR)

Your runtime app only needs:
- FastAPI/uvicorn
- psycopg2-binary (for PostgreSQL)
- faiss-cpu (for similarity search - uses pre-computed embeddings)
- Basic utilities

This should reduce the build size significantly!

