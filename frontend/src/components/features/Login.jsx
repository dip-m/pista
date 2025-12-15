// frontend/src/components/features/Login.jsx
import React, { useState } from "react";
import { authService } from "../../services/auth";

function Login({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [bggId, setBggId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isRegister) {
        await authService.register(username, password, bggId ? bggId.trim() || null : null);
      } else {
        await authService.login(username, password);
      }
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>{isRegister ? "Register" : "Login"}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
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
          {isRegister && (
            <div className="form-group">
              <label>BGG ID (optional)</label>
              <input
                type="text"
                value={bggId}
                onChange={(e) => {
                  setBggId(e.target.value);
                }}
                placeholder="Optional BoardGameGeek username or ID"
              />
            </div>
          )}
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading}>
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

