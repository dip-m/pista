// MSAL (Microsoft) OAuth Configuration
import { PublicClientApplication } from '@azure/msal-browser';

const msalConfig = {
  auth: {
    clientId: process.env.REACT_APP_MICROSOFT_CLIENT_ID || '',
    authority: `https://login.microsoftonline.com/${process.env.REACT_APP_MICROSOFT_TENANT_ID || 'common'}`,
    redirectUri: window.location.origin + '/auth/callback/microsoft',
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

// Initialize MSAL
msalInstance.initialize().then(() => {
  // Account selection logic is app dependent
});
