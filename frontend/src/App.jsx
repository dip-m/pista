import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from "react-router-dom";
import PistaChat from "./components/features/PistaChat";
import Profile from "./components/features/Profile";
import Login from "./components/features/Login";
import AdminGames from "./components/features/AdminGames";
import FeedbackAdmin from "./components/features/FeedbackAdmin";
import { authService } from "./services/auth";
import "./styles/index.css";
import "./styles/dark-mode.css";

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [darkMode, setDarkMode] = useState(() => {
    // Check localStorage or system preference
    const saved = localStorage.getItem("darkMode");
    if (saved !== null) return saved === "true";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    // Apply dark mode theme
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
    localStorage.setItem("darkMode", darkMode.toString());
  }, [darkMode]);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = authService.getToken();
    if (token) {
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
    setLoading(false);
  };

  const handleLogin = async () => {
    const userData = await authService.getCurrentUser();
    setUser(userData);
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

  return (
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
                  Logout ({user.username})
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
                <Navigate to="/" replace />
              ) : (
                <Login onLogin={handleLogin} />
              )
            }
          />
          <Route
            path="/"
            element={<PistaChat user={user} />}
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
                <AdminGames user={user} onClose={() => window.history.back()} />
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
