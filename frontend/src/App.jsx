import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from "react-router-dom";
import { GoogleOAuthProvider } from '@react-oauth/google';
import { Capacitor } from '@capacitor/core';
import { App as CapacitorApp } from '@capacitor/app';
import PistaChat from "./components/features/PistaChat";
import Profile from "./components/features/Profile";
import Login from "./components/features/Login";
import OAuthCallback from "./components/features/OAuthCallback";
import AdminGames from "./components/features/AdminGames";
import FeedbackAdmin from "./components/features/FeedbackAdmin";
import ABTestAdmin from "./components/features/ABTestAdmin";
import FeatureBlacklistAdmin from "./components/features/FeatureBlacklistAdmin";
import PWAInstallPrompt from "./components/common/PWAInstallPrompt";
import { authService } from "./services/auth";
import "./styles/index.css";
import "./styles/dark-mode.css";

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

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(() => {
    try {
      // Check localStorage or system preference
      const saved = localStorage.getItem("darkMode");
      if (saved !== null) return saved === "true";
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    } catch(e) {
      return false; // Default to light mode on error
    }
  });

  useEffect(() => {
    try {
      // Apply dark mode theme
      document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
      localStorage.setItem("darkMode", darkMode.toString());
    } catch(e) {
      // Ignore errors
    }
  }, [darkMode]);

  useEffect(() => {
    const isMobile = Capacitor.isNativePlatform();

    // Process OAuth callback from deep link (pista://oauth-callback#access_token=...)
    const processDeepLinkOAuth = (url) => {
      try {
        // Parse the deep link URL: pista://oauth-callback#access_token=...
        if (url && url.includes('pista://oauth-callback')) {
          // #region agent log
          DEBUG_LOG('App.jsx:67', 'Deep link OAuth callback detected', { url: url.substring(0, 200) }, 'C');
          // #endregion

          // Extract hash from URL (everything after #)
          const hashIndex = url.indexOf('#');
          if (hashIndex !== -1) {
            const hash = url.substring(hashIndex);
            // Clear the oauth_redirect_pending flag since we're processing the callback
            localStorage.removeItem('oauth_redirect_pending');
            // Redirect to login page with hash so Login component can process it
            // Use replace to avoid adding to history
            if (window.location.pathname === '/login') {
              // Already on login page, just update the hash
              window.location.hash = hash;
            } else {
              // Navigate to login with hash
              window.location.replace('/login' + hash);
            }
          }
        }
      } catch (err) {
        // #region agent log
        DEBUG_LOG('App.jsx:77', 'Error processing deep link OAuth', { error: err.message || String(err) }, 'E');
        // #endregion
        console.error('Error processing deep link OAuth:', err);
      }
    };

    // Listen for deep links (app opened via custom URL scheme)
    let appUrlListener = null;
    if (isMobile) {
      appUrlListener = CapacitorApp.addListener('appUrlOpen', (event) => {
        // #region agent log
        DEBUG_LOG('App.jsx:87', 'App opened via URL', { url: event.url }, 'C');
        // #endregion
        processDeepLinkOAuth(event.url);
      });
    }

    // Check for OAuth callback (mobile redirect flow from web)
    const checkOAuthCallback = () => {
      const hash = window.location.hash;
      const url = window.location.href;
      const isRedirectPage = url.includes('pistatabletop.netlify.app');

      // #region agent log
      DEBUG_LOG('App.jsx:64', 'Checking for OAuth callback in App', {
        hasHash: !!hash,
        isRedirectPage,
        isMobile,
        urlPreview: url.substring(0, 150)
      }, 'C');
      // #endregion

      // If we're on the redirect page or mobile, and have OAuth token, redirect to login to process it
      if ((isRedirectPage || isMobile) && hash && hash.includes('access_token=')) {
        // #region agent log
        DEBUG_LOG('App.jsx:75', 'OAuth callback detected - redirecting to login', {}, 'C');
        // #endregion
        // Redirect to login page with hash so Login component can process it
        // The hash will be preserved in the navigation
        if (window.location.pathname !== '/login') {
          window.location.href = '/login' + hash;
        }
      }
    };

    checkOAuthCallback();

    // On mobile, also check periodically for OAuth callback (in case app resumes)
    let intervalId = null;
    if (isMobile) {
      // Check every 2 seconds for OAuth callback when on mobile
      intervalId = setInterval(() => {
        checkOAuthCallback();
      }, 2000);
    }

    checkAuth();

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
      if (appUrlListener) {
        appUrlListener.remove();
      }
    };
  }, []);

  const checkAuth = async () => {
    try {
      const token = authService.getToken();
      if (token) {
        // Check if token is expired
        if (authService.isTokenExpired && authService.isTokenExpired()) {
          authService.logout();
        } else {
          try {
            const userData = await authService.getCurrentUser();
            if (userData) {
              setUser(userData);
            } else {
              authService.logout();
            }
          } catch (err) {
            authService.logout();
          }
        }
      }
      setLoading(false);
    } catch(err) {
      setLoading(false);
    }
  };

  const handleLogin = async (isNewUser = false) => {
    const userData = await authService.getCurrentUser();
    setUser(userData);
    // Always redirect to chat after login (profile redirect happens in route if needed)
    return userData;
  };

  // Callback to update user when BGG ID changes
  const handleUserUpdate = async () => {
    const userData = await authService.getCurrentUser();
    if (userData) {
      setUser(userData);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setUser(null);
  };

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';
  // #region agent log
  DEBUG_LOG('App.jsx:96', 'GoogleOAuthProvider clientId', { googleClientId: googleClientId ? 'SET' : 'EMPTY', length: googleClientId.length, isPlaceholder: !googleClientId }, 'D');
  // #endregion

  // Always render GoogleOAuthProvider (required for useGoogleLogin hook)
  // Use placeholder if no client ID is configured - button will be hidden in Login component
  try {
    return (
      <GoogleOAuthProvider clientId={googleClientId || 'placeholder-for-hook-compatibility'}>
        <Router>
          <div className="App">
        <nav className="app-nav">
          <div className="nav-brand">
            <Link to="/">Pista</Link>
          </div>
          <div className="nav-links">
            <Link to="/">Chat</Link>
            {user ? (
              <>
                <Link to="/profile">Profile</Link>
                {user.is_admin && (
                  <>
                    <Link to="/admin">Admin Games</Link>
                    <Link to="/admin/feedback">Admin Feedback</Link>
                    <Link to="/admin/ab-test">A/B Tests</Link>
                    <Link to="/admin/feature-blacklist">Feature Blacklist</Link>
                  </>
                )}
                <button
                  onClick={() => setDarkMode(!darkMode)}
                  className="theme-toggle"
                  title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
                >
                  {darkMode ? "☀️" : "🌙"}
                </button>
                <button onClick={handleLogout} className="logout-button">
                  Logout ({user.username || user.email || "User"})
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setDarkMode(!darkMode)}
                  className="theme-toggle"
                  title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
                >
                  {darkMode ? "☀️" : "🌙"}
                </button>
                <Link to="/login">Login</Link>
              </>
            )}
          </div>
        </nav>

        <Routes>
          <Route
            path="/login"
            element={
              user ? (
                // Redirect based on whether user has set a username
                (user.username && user.username !== user.email) ? (
                  <Navigate to="/" replace />
                ) : (
                  <Navigate to="/profile" replace />
                )
              ) : (
                <Login onLogin={handleLogin} />
              )
            }
          />
          <Route
            path="/oauth-callback"
            element={<OAuthCallback />}
          />
          <Route
            path="/"
            element={
              user ? (
                // If user doesn't have a username set, redirect to profile
                (!user.username || user.username === user.email) ? (
                  <Navigate to="/profile" replace />
                ) : (
                  <PistaChat user={user} />
                )
              ) : (
                // Allow anonymous access to chat
                <PistaChat user={null} />
              )
            }
          />
          <Route
            path="/profile"
            element={
              user ? (
                <Profile user={user} onUserUpdate={handleUserUpdate} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/admin"
            element={
              user && user.is_admin ? (
                <AdminGames user={user} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/admin/feedback"
            element={
              user && user.is_admin ? (
                <FeedbackAdmin user={user} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/admin/ab-test"
            element={
              user && user.is_admin ? (
                <ABTestAdmin user={user} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/admin/feature-blacklist"
            element={
              user && user.is_admin ? (
                <FeatureBlacklistAdmin user={user} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <PWAInstallPrompt />
          </div>
        </Router>
    </GoogleOAuthProvider>
    );
  } catch(e) {
    return <div>Error loading app: {e.message}</div>;
  }
}

export default App;
