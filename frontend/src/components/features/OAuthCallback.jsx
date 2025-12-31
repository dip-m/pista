// frontend/src/components/features/OAuthCallback.jsx
import { useEffect } from 'react';

function OAuthCallback() {
  useEffect(() => {
    const hash = window.location.hash;

    // If we're on /oauth-callback with a token, it's from mobile OAuth (system browser)
    // Web users use popup flow and never hit this page
    // So we should always redirect to custom URL scheme to open the app
    if (hash && hash.includes('access_token=')) {
      // Redirect to custom URL scheme to open the app
      const customUrl = `pista://oauth-callback${hash}`;
      console.log('[OAuthCallback] Redirecting to custom URL scheme:', customUrl.substring(0, 100));
      window.location.href = customUrl;
    } else if (hash) {
      // Check for error
      const params = new URLSearchParams(hash.substring(1));
      const error = params.get('error');
      if (error) {
        // Redirect to app with error
        const customUrl = `pista://oauth-callback${hash}`;
        console.log('[OAuthCallback] Redirecting to app with error:', error);
        window.location.href = customUrl;
      } else {
        // No token or error, redirect to login
        window.location.href = '/login';
      }
    } else {
      // No hash, redirect to login
      window.location.href = '/login';
    }
  }, []);

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      flexDirection: 'column',
      gap: '20px'
    }}>
      <div>Processing OAuth callback...</div>
      <div style={{ fontSize: '14px', color: '#666' }}>Please wait...</div>
    </div>
  );
}

export default OAuthCallback;
