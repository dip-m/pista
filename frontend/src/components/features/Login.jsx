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
        // #region agent log
        console.log('[DEBUG] Register attempt:', {username, bggId, bggIdType: typeof bggId});
        fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Login.jsx:19','message':'Register attempt',data:{username,bggId,bggIdType:typeof bggId},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'B'})}).catch(()=>{});
        // #endregion
        await authService.register(username, password, bggId ? bggId.trim() || null : null);
      } else {
        await authService.login(username, password);
      }
      onLogin();
    } catch (err) {
      // #region agent log
      console.error('[DEBUG] Register error:', err);
      fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Login.jsx:26','message':'Register error',data:{error:err.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
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
                  // #region agent log
                  console.log('[DEBUG] BGG ID input onChange:', e.target.value);
                  fetch('http://127.0.0.1:7242/ingest/d77548c2-ca0a-4d35-a70c-31fb8e09f3a3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Login.jsx:62','message':'BGG ID input onChange',data:{value:e.target.value},timestamp:Date.now(),sessionId:'debug-session',runId:'run2',hypothesisId:'B'})}).catch(()=>{});
                  // #endregion
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

