# Google OAuth Setup Guide

Complete guide for setting up Google OAuth login for Pista.

## Overview

This guide will help you configure Google OAuth so users can sign in with their Google accounts on both web and mobile platforms.

## Prerequisites

- A Google Cloud Platform account
- Access to [Google Cloud Console](https://console.cloud.google.com/)
- Your frontend domain: `https://pistatabletop.netlify.app`

## Step 1: Create OAuth 2.0 Credentials

1. **Go to Google Cloud Console**
   - Navigate to [Google Cloud Console](https://console.cloud.google.com/)
   - Select your project (or create a new one)

2. **Enable Google+ API** (if not already enabled)
   - Go to **APIs & Services** > **Library**
   - Search for "Google+ API" or "Google Identity"
   - Click **Enable**

3. **Create OAuth 2.0 Client ID**
   - Go to **APIs & Services** > **Credentials**
   - Click **+ CREATE CREDENTIALS** > **OAuth client ID**
   - If prompted, configure the OAuth consent screen first:
     - Choose **External** (unless you have a Google Workspace)
     - Fill in required fields (App name, User support email, Developer contact)
     - Add scopes: `email`, `profile`, `openid`
     - Add test users if in testing mode

4. **Configure OAuth Client**
   - **Application type**: Select **Web application**
   - **Name**: Give it a name (e.g., "Pista Web Client")
   - **Authorized JavaScript origins**: Add:
     - `http://localhost:3000` (for local development)
     - `https://pistatabletop.netlify.app` (for production)
   - **Authorized redirect URIs**: Add:
     - `http://localhost:3000` (for local development)
     - `https://pistatabletop.netlify.app` (for production web)
     - `https://pistatabletop.netlify.app/oauth-callback` (for mobile app - this page redirects to custom URL scheme)

5. **Save and Copy Client ID**
   - Click **Create**
   - Copy the **Client ID** (you'll need this for the frontend)
   - **Note**: You don't need the Client Secret for frontend OAuth (it's only used for server-side flows)

## Step 2: Configure Frontend Environment Variables

### For Local Development

1. **Create `.env` file** in the `frontend/` directory:
   ```bash
   cd frontend
   touch .env
   ```

2. **Add your Google Client ID**:
   ```env
   REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id-here.apps.googleusercontent.com
   REACT_APP_API_BASE_URL=http://localhost:8000
   ```

3. **Restart the development server**:
   ```bash
   npm start
   ```

### For Production (Netlify)

1. **Go to Netlify Dashboard**
   - Navigate to your site settings
   - Go to **Environment variables**

2. **Add environment variables**:
   - `REACT_APP_GOOGLE_CLIENT_ID`: Your Google Client ID
   - `REACT_APP_API_BASE_URL`: Your backend API URL

3. **Redeploy your site** (or wait for automatic deployment)

## Step 3: Verify Setup

1. **Check the Login Page**
   - Visit your login page
   - You should see a "Continue with Google" button
   - The button should be enabled (not grayed out)

2. **Test Google Login**
   - Click "Continue with Google"
   - You should be redirected to Google's sign-in page
   - After signing in, you should be redirected back to your app
   - You should be logged in successfully

## Troubleshooting

### Error: "redirect_uri_mismatch"

**Problem**: The redirect URI in your app doesn't match what's configured in Google Cloud Console.

**Solution**:
1. Check the exact URL where your app is running
2. Go to Google Cloud Console > Credentials > Your OAuth Client
3. Ensure the redirect URI matches exactly (including `http` vs `https`, port numbers, trailing slashes)
4. For production, use: `https://pistatabletop.netlify.app`
5. For local development, use: `http://localhost:3000`

### Error: "Google OAuth is not configured"

**Problem**: The `REACT_APP_GOOGLE_CLIENT_ID` environment variable is not set.

**Solution**:
1. Check that you've created a `.env` file in the `frontend/` directory
2. Verify the variable name is exactly `REACT_APP_GOOGLE_CLIENT_ID`
3. Restart your development server after adding the variable
4. For production, ensure the variable is set in your deployment platform (Netlify, Vercel, etc.)

### Button is Grayed Out

**Problem**: The Google OAuth button is disabled.

**Solution**:
- This happens when `REACT_APP_GOOGLE_CLIENT_ID` is not set
- Follow the steps in "Configure Frontend Environment Variables" above

### OAuth Works on Web but Not Mobile

**Problem**: OAuth works in browser but fails in the mobile app, or login redirects to web app instead of returning to mobile app.

**Solution**:
- Ensure `https://pistatabletop.netlify.app/oauth-callback` is added to **Authorized redirect URIs** in Google Cloud Console
- The mobile app uses the system browser for OAuth (not WebView) and returns via custom URL scheme
- Verify the custom URL scheme is configured in `AndroidManifest.xml` (Android) and `Info.plist` (iOS)
- Check that `@capacitor/browser` and `@capacitor/app` plugins are installed: `npm install @capacitor/browser @capacitor/app`

## Mobile App Configuration

For Capacitor mobile apps (Android/iOS):

1. **Use the same OAuth client** as your web app
2. **Add the OAuth callback page URL** to authorized redirect URIs in Google Cloud Console:
   - `https://pistatabletop.netlify.app/oauth-callback`
3. **How it works**:
   - The mobile app opens OAuth in the system browser (not WebView)
   - After successful authentication, Google redirects to `https://pistatabletop.netlify.app/oauth-callback?mobile=true#access_token=...`
   - The callback page detects it's a mobile OAuth callback and redirects to `pista://oauth-callback#access_token=...`
   - The custom URL scheme opens the app, which processes the OAuth token
   - This ensures users return to the native app after login instead of staying in the web app

**Important**: 
- The OAuth callback page URL (`https://pistatabletop.netlify.app/oauth-callback`) must be added to the **Authorized redirect URIs** in Google Cloud Console
- Google OAuth requires HTTPS URLs, so we use the web URL as the redirect URI, then redirect to the custom URL scheme

## Security Notes

- ✅ **Client ID is safe to expose** - It's public and used in frontend code
- ❌ **Never expose Client Secret** - Only use it in backend/server-side code
- ✅ **HTTPS required in production** - Google requires HTTPS for production redirect URIs
- ✅ **Token verification** - The backend verifies OAuth tokens server-side for security

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 for Mobile & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)

## Quick Checklist

- [ ] Created OAuth 2.0 Client ID in Google Cloud Console
- [ ] Added redirect URIs: `http://localhost:3000`, `https://pistatabletop.netlify.app`, and `https://pistatabletop.netlify.app/oauth-callback`
- [ ] Set `REACT_APP_GOOGLE_CLIENT_ID` in frontend `.env` file
- [ ] Installed `@capacitor/browser` and `@capacitor/app` plugins: `npm install @capacitor/browser @capacitor/app`
- [ ] Configured custom URL scheme in AndroidManifest.xml (Android) and Info.plist (iOS)
- [ ] Restarted development server
- [ ] Tested Google login on web
- [ ] Tested Google login on mobile (if applicable) - verify it returns to app after login
- [ ] Verified user can sign in and access the app
