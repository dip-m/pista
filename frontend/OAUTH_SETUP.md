# OAuth Setup Guide for Frontend

## Overview

The frontend has been updated to support OAuth authentication (Google, Microsoft, Meta) and email-based login. The OAuth buttons are currently placeholders and need proper OAuth SDK integration.

## Current Status

✅ **Completed:**
- Email registration and login endpoints updated
- OAuth callback structure in place
- Login UI updated with OAuth buttons and email form

❌ **Needs Implementation:**
- OAuth provider SDKs installation
- OAuth flow implementation for each provider

## Required OAuth Libraries

### Option 1: Individual SDKs (Recommended for Production)

#### Google OAuth
```bash
npm install @react-oauth/google
```

#### Microsoft OAuth
```bash
npm install @azure/msal-browser @azure/msal-react
```

#### Meta/Facebook OAuth
```bash
npm install react-facebook-login
```

### Option 2: Universal OAuth Library

Alternatively, you can use a universal OAuth library like `react-oauth` or implement a custom solution.

## Implementation Steps

### 1. Google OAuth Setup

1. **Install the library:**
   ```bash
   npm install @react-oauth/google
   ```

2. **Get Google OAuth credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 credentials
   - Add authorized redirect URI: `https://your-frontend.netlify.app/auth/callback/google`
   - Get Client ID

3. **Update `Login.jsx`:**
   ```jsx
   import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';

   // In Login component:
   const googleLogin = useGoogleLogin({
     onSuccess: async (tokenResponse) => {
       try {
         // Get user info from Google
         const userInfo = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
           headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
         }).then(res => res.json());
         
         // Send to backend
         await authService.oauthCallback(
           'google',
           tokenResponse.access_token,
           userInfo.email,
           userInfo.name
         );
         onLogin();
       } catch (err) {
         setError(err.message);
       }
     },
     onError: () => setError('Google login failed')
   });
   ```

4. **Wrap App with GoogleOAuthProvider in `App.jsx`:**
   ```jsx
   import { GoogleOAuthProvider } from '@react-oauth/google';

   function App() {
     return (
       <GoogleOAuthProvider clientId="YOUR_GOOGLE_CLIENT_ID">
         {/* ... rest of app */}
       </GoogleOAuthProvider>
     );
   }
   ```

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
