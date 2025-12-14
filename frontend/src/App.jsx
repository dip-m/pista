import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from "react-router-dom";
import PistaChat from "./components/PistaChat";
import Profile from "./components/Profile";
import Login from "./components/Login";
import { authService } from "./auth";
import "./components/index.css";

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

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
            <Link to="/">Pista - Game Sommelier</Link>
          </div>
          <div className="nav-links">
            <Link to="/">Chat</Link>
            {user ? (
              <>
                <Link to="/profile">Profile</Link>
                <button onClick={handleLogout} className="logout-button">
                  Logout ({user.username})
                </button>
              </>
            ) : (
              <Link to="/login">Login</Link>
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
