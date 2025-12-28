import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from "react-router-dom";
import { GoogleOAuthProvider } from '@react-oauth/google';
import { MsalProvider } from '@azure/msal-react';
import { msalInstance } from './config/msalConfig';
import PistaChat from "./components/features/PistaChat";
import Profile from "./components/features/Profile";
import Login from "./components/features/Login";
import AdminGames from "./components/features/AdminGames";
import FeedbackAdmin from "./components/features/FeedbackAdmin";
import ABTestAdmin from "./components/features/ABTestAdmin";
import PWAInstallPrompt from "./components/common/PWAInstallPrompt";
import { authService } from "./services/auth";
import { debugLog, debugError } from "./utils/debugLog";
import "./styles/index.css";
import "./styles/dark-mode.css";

function App() {
  // #region agent log
  debugLog('App.jsx:19','App component initializing',{hasWindow:typeof window!=='undefined',hasDocument:typeof document!=='undefined'},'A');
  // #endregion

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(() => {
    // #region agent log
    debugLog('App.jsx:27','Before localStorage access in darkMode init',{hasLocalStorage:typeof localStorage!=='undefined'},'D');
    // #endregion
    try {
      // Check localStorage or system preference
      const saved = localStorage.getItem("darkMode");
      // #region agent log
      debugLog('App.jsx:31','localStorage.getItem completed',{saved:saved!==null?saved:'null'},'D');
      // #endregion
      if (saved !== null) return saved === "true";
      // #region agent log
      const matchMediaResult = window.matchMedia("(prefers-color-scheme: dark)").matches;
      debugLog('App.jsx:35','matchMedia check completed',{matches:matchMediaResult},'D');
      // #endregion
      return matchMediaResult;
    } catch(e) {
      // #region agent log
      debugError('App.jsx:34','localStorage/matchMedia error in darkMode init',e,'D');
      // #endregion
      return false; // Default to light mode on error
    }
  });

  useEffect(() => {
    // #region agent log
    debugLog('App.jsx:53','darkMode useEffect executing',{darkMode},'D');
    // #endregion
    try {
      // Apply dark mode theme
      document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
      localStorage.setItem("darkMode", darkMode.toString());
      // #region agent log
      debugLog('App.jsx:59','darkMode localStorage.setItem completed',{success:true},'D');
      // #endregion
    } catch(e) {
      // #region agent log
      debugError('App.jsx:48','darkMode useEffect error',e,'D');
      // #endregion
    }
  }, [darkMode]);

  useEffect(() => {
    // #region agent log
    debugLog('App.jsx:73','checkAuth useEffect starting',{},'A');
    // #endregion
    checkAuth();
  }, []);

  const checkAuth = async () => {
    // #region agent log
    debugLog('App.jsx:80','checkAuth function entry',{},'A');
    // #endregion
    try {
      const token = authService.getToken();
      // #region agent log
      debugLog('App.jsx:85','Token retrieved',{hasToken:!!token},'A');
      // #endregion
      if (token) {
        // Check if token is expired
        if (authService.isTokenExpired && authService.isTokenExpired()) {
          authService.logout();
        } else {
          try {
            const userData = await authService.getCurrentUser();
            // #region agent log
            debugLog('App.jsx:95','getCurrentUser completed',{hasUserData:!!userData},'A');
            // #endregion
            if (userData) {
              setUser(userData);
            } else {
              authService.logout();
            }
          } catch (err) {
            // #region agent log
            debugError('App.jsx:78','getCurrentUser error',err,'E');
            // #endregion
            authService.logout();
          }
        }
      }
      setLoading(false);
      // #region agent log
      debugLog('App.jsx:112','checkAuth completed successfully',{loading:false},'A');
      // #endregion
    } catch(err) {
      // #region agent log
      debugError('App.jsx:87','checkAuth exception',err,'A');
      // #endregion
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
  debugLog('App.jsx:143','Before render - checking env vars and providers',{googleClientId:googleClientId||'empty',hasMsalInstance:!!msalInstance},'C');
  // #endregion

  // Always render GoogleOAuthProvider (required for useGoogleLogin hook)
  // Use placeholder if no client ID is configured - button will be hidden in Login component
  try {
    return (
      <GoogleOAuthProvider clientId={googleClientId || 'placeholder-for-hook-compatibility'}>
        <MsalProvider instance={msalInstance}>
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <PWAInstallPrompt />
          </div>
        </Router>
      </MsalProvider>
    </GoogleOAuthProvider>
    );
  } catch(e) {
    // #region agent log
    debugError('App.jsx:213','Render exception',e,'A');
    // #endregion
    return <div>Error loading app: {e.message}</div>;
  }
}

export default App;
