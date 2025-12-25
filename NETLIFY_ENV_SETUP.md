# Netlify Environment Variables Setup

## Required Environment Variable

The frontend needs to know the backend API URL. Set this in Netlify:

### Steps:

1. Go to [Netlify Dashboard](https://app.netlify.com)
2. Select your site: `pistatabletop`
3. Go to **Site settings** → **Environment variables**
4. Click **Add a variable**
5. Add:
   - **Key**: `REACT_APP_API_BASE_URL`
   - **Value**: `https://web-production-f74f5.up.railway.app`
6. Click **Save**
7. **Redeploy** your site (go to **Deploys** → **Trigger deploy** → **Deploy site**)

### Why This Is Needed

The frontend code uses:
```javascript
export const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
```

Without this environment variable, the frontend defaults to `http://localhost:8000`, which won't work in production.

### Verification

After setting the variable and redeploying:
1. Open `https://pistatabletop.netlify.app/login`
2. Open browser DevTools (F12) → Console
3. You should see logs showing the correct API_BASE URL (not localhost:8000)

