# Environment Variables Setup

## Required Environment Variables

Create a `.env` file in the `frontend` directory (or set these in Netlify for production):

```env
# Google OAuth (Required for Google login)
REACT_APP_GOOGLE_CLIENT_ID=your_google_client_id_here

# Microsoft OAuth (Optional - for Microsoft login)
REACT_APP_MICROSOFT_CLIENT_ID=your_microsoft_client_id_here
REACT_APP_MICROSOFT_TENANT_ID=your_tenant_id_or_common

# API Base URL
REACT_APP_API_BASE_URL=http://localhost:8000
# For production: REACT_APP_API_BASE_URL=https://your-backend.onrender.com
```

## Quick Setup

1. **Create `.env` file** in `frontend/` directory:
   ```bash
   cd frontend
   touch .env
   ```

2. **Add your Google Client ID**:
   ```env
   REACT_APP_GOOGLE_CLIENT_ID=your_google_client_id_here
   REACT_APP_API_BASE_URL=http://localhost:8000
   ```

3. **Restart the development server**:
   ```bash
   npm start
   ```

## For Production (Netlify)

Add these environment variables in Netlify dashboard:
- `REACT_APP_GOOGLE_CLIENT_ID`
- `REACT_APP_MICROSOFT_CLIENT_ID` (if using Microsoft login)
- `REACT_APP_MICROSOFT_TENANT_ID` (if using Microsoft login)
- `REACT_APP_API_BASE_URL` (your backend URL)

## Notes

- All `REACT_APP_*` variables are exposed to the browser (public)
- Never put secrets in `REACT_APP_*` variables
- The `.env` file should be in `.gitignore` (don't commit it)
