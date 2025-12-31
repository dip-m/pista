# OAuth Setup Guide for Frontend

## Overview

The frontend supports OAuth authentication (Google, Microsoft, Meta) and email-based login. OAuth is fully implemented and ready to use.

## Current Status

✅ **Completed:**
- Email registration and login endpoints
- OAuth callback structure
- Google OAuth fully implemented with `@react-oauth/google`
- Microsoft OAuth implemented with `@azure/msal-browser`
- Login UI with OAuth buttons and email form
- Error handling and user feedback

## Quick Setup

For detailed Google OAuth setup instructions, see:
- **[Google OAuth Setup Guide](./GOOGLE_OAUTH_SETUP.md)** - Complete step-by-step guide

## Google OAuth (✅ Implemented)

Google OAuth is fully implemented and ready to use. You just need to configure your Google Client ID.

### Quick Setup

1. **Get your Google Client ID:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create OAuth 2.0 credentials (Web application type)
   - Add authorized redirect URIs:
     - `http://localhost:3000` (for development)
     - `https://pistatabletop.netlify.app` (for production)

2. **Set environment variable:**
   ```env
   REACT_APP_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   ```

3. **Restart your development server**

### Detailed Setup

For complete step-by-step instructions, troubleshooting, and mobile app configuration, see:
- **[Google OAuth Setup Guide](./GOOGLE_OAUTH_SETUP.md)**

### Implementation Details

- ✅ Uses `@react-oauth/google` library (already installed)
- ✅ Configured in `App.jsx` with `GoogleOAuthProvider`
- ✅ OAuth flow implemented in `Login.jsx`
- ✅ Backend verification in `backend/auth_utils.py`
- ✅ Works on both web and mobile (Capacitor) platforms

### 2. Microsoft OAuth Setup

1. **Install the library:**
   ```bash
   npm install @azure/msal-browser @azure/msal-react
   ```

2. **Get Microsoft OAuth credentials:**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Register an app
   - Add redirect URI: `https://your-frontend.netlify.app/auth/callback/microsoft`
   - Get Client ID and Tenant ID

3. **Create MSAL configuration:**
   ```jsx
   // Create msalConfig.js
   import { PublicClientApplication } from '@azure/msal-browser';

   export const msalConfig = {
     auth: {
       clientId: 'YOUR_MICROSOFT_CLIENT_ID',
       authority: 'https://login.microsoftonline.com/YOUR_TENANT_ID',
       redirectUri: window.location.origin + '/auth/callback/microsoft'
     }
   };

   export const msalInstance = new PublicClientApplication(msalConfig);
   ```

4. **Update `Login.jsx`:**
   ```jsx
   import { useMsal } from '@azure/msal-react';

   // In Login component:
   const { instance } = useMsal();
   
   const handleMicrosoftLogin = async () => {
     try {
       const response = await instance.loginPopup({
         scopes: ['User.Read']
       });
       
       await authService.oauthCallback(
         'microsoft',
         response.accessToken,
         response.account.username,
         response.account.name
       );
       onLogin();
     } catch (err) {
       setError(err.message);
     }
   };
   ```

5. **Wrap App with MsalProvider in `App.jsx`:**
   ```jsx
   import { MsalProvider } from '@azure/msal-react';
   import { msalInstance } from './msalConfig';

   function App() {
     return (
       <MsalProvider instance={msalInstance}>
         {/* ... rest of app */}
       </MsalProvider>
     );
   }
   ```

### 3. Meta/Facebook OAuth Setup

1. **Install the library:**
   ```bash
   npm install react-facebook-login
   ```

2. **Get Meta OAuth credentials:**
   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create an app
   - Add redirect URI: `https://your-frontend.netlify.app/auth/callback/meta`
   - Get App ID

3. **Update `Login.jsx`:**
   ```jsx
   import FacebookLogin from 'react-facebook-login';

   // In Login component:
   const responseFacebook = async (response) => {
     try {
       await authService.oauthCallback(
         'meta',
         response.accessToken,
         response.email,
         response.name
       );
       onLogin();
     } catch (err) {
       setError(err.message);
     }
   };

   // In JSX:
   <FacebookLogin
     appId="YOUR_META_APP_ID"
     autoLoad={false}
     fields="name,email"
     callback={responseFacebook}
     cssClass="oauth-button meta"
     textButton="Continue with Meta"
   />
   ```

## Environment Variables

Add to your `.env` or Netlify environment variables:

```env
REACT_APP_GOOGLE_CLIENT_ID=your_google_client_id
REACT_APP_MICROSOFT_CLIENT_ID=your_microsoft_client_id
REACT_APP_MICROSOFT_TENANT_ID=your_tenant_id
REACT_APP_META_APP_ID=your_meta_app_id
REACT_APP_API_BASE_URL=https://your-backend.onrender.com
```

## Testing

1. **Email Login/Register**: ✅ Should work immediately
2. **OAuth**: Requires SDK installation and configuration as above

## Notes

- The current implementation shows OAuth buttons but throws errors when clicked (as expected)
- Once OAuth SDKs are installed and configured, the buttons will work
- All OAuth flows send tokens to `/auth/oauth/callback` which handles user creation/login
- The backend verifies OAuth tokens server-side for security

## Security Considerations

- Never expose OAuth client secrets in frontend code
- Always verify OAuth tokens on the backend (already implemented)
- Use HTTPS in production
- Validate redirect URIs match exactly
