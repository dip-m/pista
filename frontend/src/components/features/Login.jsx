// frontend/src/components/features/Login.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGoogleLogin } from '@react-oauth/google';
import { Capacitor } from '@capacitor/core';
import { Browser } from '@capacitor/browser';
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";
import { httpRequest } from "../../utils/httpClient";

// #region agent log
const DEBUG_LOG = (location, message, data, hypothesisId) => {
  const logData = {
    location,
    message,
    data: { ...data, isMobile: Capacitor.isNativePlatform() },
    timestamp: Date.now(),
    sessionId: 'debug-session',
    runId: 'run1',
    hypothesisId
  };
  console.log('[DEBUG]', JSON.stringify(logData));
  fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(logData)
  }).catch(() => {});
};
// #endregion

function Login({ onLogin }) {
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(null);
  const [rememberMe, setRememberMe] = useState(false);
  const [bggUsername, setBggUsername] = useState("");

  // Check if running on mobile (Capacitor native platform)
  const isMobile = Capacitor.isNativePlatform();

  // Handle OAuth callback from redirect (mobile)
  React.useEffect(() => {
    const checkOAuthCallback = () => {
      const hash = window.location.hash;
      const url = window.location.href;
      const origin = window.location.origin;
      // #region agent log
      DEBUG_LOG('Login.jsx:42', 'Checking for OAuth callback', {
        hasHash: !!hash,
        hashLength: hash?.length,
        origin,
        urlPreview: url.substring(0, 150),
        isMobile,
        urlIncludesNetlify: url.includes('pistatabletop.netlify.app')
      }, 'C');
      // #endregion

      // Check if we're on the redirect URI page (web app loaded in WebView) OR if we have OAuth token in hash
      // This handles both: WebView navigating to web app, and direct hash in current page
      const isRedirectPage = url.includes('pistatabletop.netlify.app');
      const hasOAuthToken = hash && hash.includes('access_token=');

      if ((isRedirectPage || isMobile) && hasOAuthToken) {
        // #region agent log
        DEBUG_LOG('Login.jsx:60', 'OAuth callback detected - processing token', {
          hashPreview: hash.substring(0, 80),
          isRedirectPage,
          isMobile,
          url
        }, 'C');
        // #endregion
        const params = new URLSearchParams(hash.substring(1));
        const accessToken = params.get('access_token');
        const error = params.get('error');
        const errorDescription = params.get('error_description');

        if (error) {
          // #region agent log
          DEBUG_LOG('Login.jsx:72', 'OAuth error in callback', { error, errorDescription }, 'C');
          // #endregion
          setError(`OAuth error: ${error}. ${errorDescription || ''}`);
          setOauthLoading(null);
          window.history.replaceState(null, '', window.location.pathname);
          localStorage.removeItem('oauth_redirect_pending');
          return;
        }

        if (accessToken) {
          setOauthLoading("google");
          setError("");
          // Process the OAuth token (same as onSuccess handler)
          (async () => {
            try {
              // Get user info from Google
              const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
                headers: { Authorization: `Bearer ${accessToken}` }
              });

              if (!userInfoResponse.ok) {
                throw new Error('Failed to fetch user info from Google');
              }

              const userInfo = await userInfoResponse.json();

              if (!userInfo.email) {
                throw new Error('Google account email not found.');
              }

              // Send to backend
              const result = await authService.oauthCallback(
                'google',
                accessToken,
                userInfo.email,
                userInfo.name || userInfo.email
              );
              await onLogin(result.is_new_user || false);
              // Clear hash from URL
              window.history.replaceState(null, '', window.location.pathname);
              localStorage.removeItem('oauth_redirect_pending');
              navigate("/");
            } catch (err) {
              // #region agent log
              DEBUG_LOG('Login.jsx:55', 'OAuth callback processing failed', { error: err.message || String(err) }, 'C');
              // #endregion
              console.error('Google OAuth callback error:', err);
              setError(err.message || 'Google login failed. Please try again.');
              setOauthLoading(null);
              // Clear hash from URL
              window.history.replaceState(null, '', window.location.pathname);
              localStorage.removeItem('oauth_redirect_pending');
            }
          })();
        }
      } else if (url.includes('pistatabletop.netlify.app') && hash) {
        // We're on the redirect page but no token - might be an error
        const params = new URLSearchParams(hash.substring(1));
        const error = params.get('error');
        if (error) {
          // #region agent log
          DEBUG_LOG('Login.jsx:115', 'OAuth error on redirect page', { error, errorDescription: params.get('error_description') }, 'C');
          // #endregion
          setError(`OAuth error: ${error}. ${params.get('error_description') || ''}`);
          setOauthLoading(null);
          window.history.replaceState(null, '', window.location.pathname);
          localStorage.removeItem('oauth_redirect_pending');
        }
      }
    };

    // Check immediately
    checkOAuthCallback();

    // Listen for hash changes (e.g., when app opens via deep link)
    const handleHashChange = () => {
      checkOAuthCallback();
    };
    window.addEventListener('hashchange', handleHashChange);

    // On mobile, also check periodically for OAuth callback
    let intervalId = null;
    if (isMobile) {
      // Check every 2 seconds for OAuth callback when on mobile
      intervalId = setInterval(() => {
        const hasPending = localStorage.getItem('oauth_redirect_pending') === 'true';
        if (hasPending) {
          // #region agent log
          DEBUG_LOG('Login.jsx:140', 'Periodic OAuth check (mobile)', { hasPending }, 'C');
          // #endregion
          checkOAuthCallback();
        }
      }, 2000);
    }

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [navigate, onLogin, isMobile]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let isNewUser = false;
      if (isRegister) {
        await authService.register(email, password, rememberMe);
        isNewUser = true;
      } else {
        await authService.login(email, password, rememberMe);
      }
      await onLogin(isNewUser);
      // Always redirect to chat after login (route will handle profile redirect if needed)
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Google OAuth handler - hook must always be called (React rules)
  const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';
  // #region agent log
  DEBUG_LOG('Login.jsx:45', 'Google Client ID loaded', { googleClientId: googleClientId ? 'SET' : 'EMPTY', length: googleClientId.length, isMobile }, 'D');
  // #endregion
  const handleGoogleLogin = useGoogleLogin({
    flow: 'implicit', // Use implicit flow (token in URL fragment)
    onSuccess: async (tokenResponse) => {
      // #region agent log
      DEBUG_LOG('Login.jsx:47', 'useGoogleLogin onSuccess called', { hasToken: !!tokenResponse?.access_token }, 'C');
      // #endregion
      if (!googleClientId) {
        // #region agent log
        DEBUG_LOG('Login.jsx:49', 'Google Client ID missing in onSuccess', {}, 'D');
        // #endregion
        setError('Google OAuth is not configured. Please set REACT_APP_GOOGLE_CLIENT_ID.');
        setOauthLoading(null);
        return;
      }
      setOauthLoading("google");
      setError("");
      try {
        // Get user info from Google
        const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
        });

        if (!userInfoResponse.ok) {
          throw new Error('Failed to fetch user info from Google');
        }

        const userInfo = await userInfoResponse.json();

        if (!userInfo.email) {
          throw new Error('Google account email not found. Please ensure your Google account has an email address.');
        }

        // Send to backend
        const result = await authService.oauthCallback(
          'google',
          tokenResponse.access_token,
          userInfo.email,
          userInfo.name || userInfo.email
        );
        await onLogin(result.is_new_user || false);
        // Always redirect to chat after login
        navigate("/");
      } catch (err) {
        console.error('Google OAuth error:', err);
        setError(err.message || 'Google login failed. Please try again.');
      } finally {
        setOauthLoading(null);
      }
    },
    onError: (error) => {
      // #region agent log
      DEBUG_LOG('Login.jsx:88', 'useGoogleLogin onError called', { errorType: error?.error, errorMessage: error?.message || String(error), isMobile, fullError: JSON.stringify(error) }, 'C');
      // #endregion
      console.error('Google OAuth error:', error);
      if (error?.error === 'popup_closed_by_user' || error?.error === 'popup_blocked') {
        // On mobile, popup is blocked - need to use redirect flow
        if (isMobile) {
          setError('Mobile OAuth requires redirect flow. Please configure redirect URI in Google Console.');
          // #region agent log
          DEBUG_LOG('Login.jsx:95', 'Popup blocked on mobile - redirect needed', {}, 'C');
          // #endregion
        } else {
          setError('Login cancelled. Please try again if you want to continue.');
        }
      } else if (error?.error === 'redirect_uri_mismatch') {
        setError(
          'Google OAuth redirect URI mismatch. ' +
          'Please add "http://localhost:3000" to both "Authorized JavaScript origins" and ' +
          '"Authorized redirect URIs" in Google Cloud Console > Credentials > OAuth 2.0 Client ID.'
        );
      } else {
        setError(`Google login failed: ${error?.error || error?.message || 'Unknown error'}. Please try again.`);
      }
      setOauthLoading(null);
    }
  });

  // BoardGameGeek login handler
  const handleBggLogin = async () => {
    if (!bggUsername.trim()) {
      setError("Please enter your BoardGameGeek username");
      return;
    }

    setError("");
    setOauthLoading("bgg");
    try {
      // BGG doesn't have OAuth, so we use the username directly
      // The backend will verify the username exists
      const result = await authService.oauthCallback(
        'bgg',
        bggUsername.trim(),  // Use username as "token"
        null,  // No email for BGG
        bggUsername.trim()  // Use username as name
      );
      const userData = await onLogin(result.is_new_user || false);

      // Auto-update collection if it's empty for BGG users
      if (userData && userData.bgg_id) {
        try {
          // Check if collection is empty
          const collectionRes = await httpRequest(`${API_BASE}/profile/collection`, {
            method: "GET",
            headers: authService.getAuthHeaders(),
          });
          if (collectionRes.ok) {
            const collection = await collectionRes.json();
            if (collection.length === 0) {
              // Collection is empty, auto-update it
              const importRes = await httpRequest(`${API_BASE}/profile/collection/import-bgg`, {
                method: "POST",
                headers: authService.getAuthHeaders(),
              });
              if (importRes.ok) {
                const importData = await importRes.json();
                console.log(`Auto-imported ${importData.added} games from BGG`);
              }
            }
          }
        } catch (err) {
          // Silently fail - collection update is not critical for login
          console.debug("Failed to auto-update collection:", err);
        }
      }

      // Always redirect to chat after login
      navigate("/");
    } catch (err) {
      setError(err.message || 'BoardGameGeek login failed. Please check your username and try again.');
    } finally {
      setOauthLoading(null);
    }
  };

  const handleOAuth = (provider) => {
    // #region agent log
    DEBUG_LOG('Login.jsx:140', 'handleOAuth called', { provider, googleClientId: googleClientId ? 'SET' : 'EMPTY', handleGoogleLoginType: typeof handleGoogleLogin, isMobile }, 'B');
    // #endregion
    if (provider === "google") {
      if (googleClientId) {
        // #region agent log
        DEBUG_LOG('Login.jsx:143', 'Calling handleGoogleLogin', { isMobile }, 'B');
        // #endregion

        // On mobile, useGoogleLogin with popup doesn't work - need redirect flow with system browser
        if (isMobile) {
          // #region agent log
          DEBUG_LOG('Login.jsx:147', 'Mobile detected - using Browser plugin for OAuth', { origin: window.location.origin, href: window.location.href }, 'C');
          // #endregion
          // For mobile, use the web URL as redirect URI (Google requires HTTPS)
          // The web page will detect it's a mobile OAuth callback and redirect to custom URL scheme
          // IMPORTANT: This must match EXACTLY what's in Google Cloud Console (no trailing slash, no query params)
          const redirectUri = 'https://pistatabletop.netlify.app/oauth-callback';
          const scope = 'openid email profile';
          const responseType = 'token';
          const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(googleClientId)}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=${responseType}&scope=${encodeURIComponent(scope)}`;

          // #region agent log
          DEBUG_LOG('Login.jsx:155', 'OAuth redirect URL constructed', {
            redirectUri,
            googleClientId: googleClientId.substring(0, 20) + '...',
            authUrlLength: authUrl.length,
            encodedRedirectUri: encodeURIComponent(redirectUri)
          }, 'C');
          // #endregion

          setOauthLoading("google");
          setError("");

          // Store OAuth state to detect when we return
          localStorage.setItem('oauth_redirect_pending', 'true');

          // Open OAuth in system browser - after OAuth completes, Google redirects to the web URL
          // The web page will detect it's a mobile callback and redirect to pista://oauth-callback
          // which will open the app and we'll handle the callback in App.jsx
          Browser.open({ url: authUrl }).catch((err) => {
            // #region agent log
            DEBUG_LOG('Login.jsx:165', 'Browser.open failed', { error: err.message || String(err) }, 'E');
            // #endregion
            console.error('Failed to open browser for OAuth:', err);
            setError('Failed to open browser for OAuth. Please try again.');
            setOauthLoading(null);
          });
          return;
        }

        try {
          handleGoogleLogin();
          // #region agent log
          DEBUG_LOG('Login.jsx:162', 'handleGoogleLogin call completed', {}, 'B');
          // #endregion
        } catch (err) {
          // #region agent log
          DEBUG_LOG('Login.jsx:165', 'handleGoogleLogin threw error', { error: err.message || String(err) }, 'E');
          // #endregion
          setError('Failed to initiate Google login: ' + (err.message || String(err)));
        }
      } else {
        // #region agent log
        DEBUG_LOG('Login.jsx:171', 'Google Client ID missing in handleOAuth', {}, 'D');
        // #endregion
        setError('Google OAuth is not configured. Please set REACT_APP_GOOGLE_CLIENT_ID.');
      }
    } else if (provider === "bgg") {
      handleBggLogin();
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>{isRegister ? "Register" : "Login"}</h2>

        {/* OAuth Buttons */}
        <div className="oauth-buttons" style={{ marginBottom: "20px" }}>
          <button
            type="button"
            className="oauth-button google"
            onClick={() => {
              // #region agent log
              DEBUG_LOG('Login.jsx:164', 'Google button onClick fired', { loading, oauthLoading, hasClientId: !!googleClientId, disabled: loading || oauthLoading || !googleClientId }, 'A');
              // #endregion
              handleOAuth("google");
            }}
            disabled={loading || oauthLoading || !googleClientId}
            style={{
              width: "100%",
              padding: "10px",
              marginBottom: "10px",
              backgroundColor: googleClientId ? "#4285F4" : "#cccccc",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: googleClientId ? "pointer" : "not-allowed",
              fontSize: "14px",
              opacity: googleClientId ? 1 : 0.6
            }}
            title={!googleClientId ? "Google OAuth is not configured" : ""}
          >
            {oauthLoading === "google" ? "Loading..." : "Continue with Google"}
          </button>
          <div style={{ marginBottom: "10px" }}>
            <input
              type="text"
              value={bggUsername}
              onChange={(e) => setBggUsername(e.target.value)}
              placeholder="BoardGameGeek Username"
              disabled={loading || oauthLoading}
              style={{
                width: "100%",
                padding: "10px",
                marginBottom: "5px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                fontSize: "14px"
              }}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !loading && !oauthLoading && bggUsername.trim()) {
                  handleBggLogin();
                }
              }}
            />
            <button
              type="button"
              className="oauth-button bgg"
              onClick={() => handleOAuth("bgg")}
              disabled={loading || oauthLoading || !bggUsername.trim()}
              style={{
                width: "100%",
                padding: "10px",
                backgroundColor: bggUsername.trim() ? "#FF6B35" : "#cccccc",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: bggUsername.trim() ? "pointer" : "not-allowed",
                fontSize: "14px",
                opacity: bggUsername.trim() ? 1 : 0.6
              }}
            >
              {oauthLoading === "bgg" ? "Loading..." : "Continue with BoardGameGeek"}
            </button>
          </div>
        </div>

        <div style={{ textAlign: "center", margin: "20px 0", color: "#666" }}>
          <span>or</span>
        </div>

        {/* Email/Password Form */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="your@email.com"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="form-group" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="checkbox"
              id="rememberMe"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            <label htmlFor="rememberMe" style={{ margin: 0, cursor: "pointer" }}>
              Remember me
            </label>
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading || oauthLoading}>
            {loading ? "Loading..." : isRegister ? "Register" : "Login"}
          </button>
        </form>
        <p className="toggle-form">
          {isRegister ? "Already have an account? " : "Don't have an account? "}
          <button
            type="button"
            className="link-button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError("");
            }}
          >
            {isRegister ? "Login" : "Register"}
          </button>
        </p>
      </div>
    </div>
  );
}

export default Login;
