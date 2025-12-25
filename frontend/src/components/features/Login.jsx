// frontend/src/components/features/Login.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGoogleLogin } from '@react-oauth/google';
import { useMsal } from '@azure/msal-react';
import { authService } from "../../services/auth";

function Login({ onLogin }) {
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(null);
  const [rememberMe, setRememberMe] = useState(false);
  
  // Microsoft MSAL hook
  const { instance } = useMsal();

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
      const userData = await onLogin(isNewUser);
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
  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      if (!googleClientId) {
        setError('Google OAuth is not configured.');
        setOauthLoading(null);
        return;
      }
      setOauthLoading("google");
      setError("");
      try {
        // Get user info from Google
        const userInfo = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
        }).then(res => res.json());
        
        // Send to backend
        const result = await authService.oauthCallback(
          'google',
          tokenResponse.access_token,
          userInfo.email,
          userInfo.name
        );
        const userData = await onLogin(result.is_new_user || false);
        // Always redirect to chat after login
        navigate("/");
      } catch (err) {
        setError(err.message || 'Google login failed');
      } finally {
        setOauthLoading(null);
      }
    },
    onError: () => {
      setError('Google login failed');
      setOauthLoading(null);
    }
  });

  // Microsoft OAuth handler
  const handleMicrosoftLogin = async () => {
    setError("");
    setOauthLoading("microsoft");
    try {
      const response = await instance.loginPopup({
        scopes: ['User.Read'],
        account: instance.getActiveAccount()
      });
      
      // Get user info from Microsoft Graph
      const userInfo = await fetch('https://graph.microsoft.com/v1.0/me', {
        headers: { Authorization: `Bearer ${response.accessToken}` }
      }).then(res => res.json());
      
      const result = await authService.oauthCallback(
        'microsoft',
        response.accessToken,
        userInfo.mail || userInfo.userPrincipalName,
        userInfo.displayName
      );
      const userData = await onLogin(result.is_new_user || false);
      // Always redirect to chat after login
      navigate("/");
    } catch (err) {
      setError(err.message || 'Microsoft login failed. Please configure Microsoft OAuth credentials.');
    } finally {
      setOauthLoading(null);
    }
  };

  // Meta/Facebook OAuth handler
  const handleMetaLogin = () => {
    setError("");
    setOauthLoading("meta");
    setError('Meta OAuth requires react-facebook-login. Please install: npm install react-facebook-login');
    setOauthLoading(null);
  };

  const handleOAuth = (provider) => {
    if (provider === "google") {
      if (googleClientId) {
        handleGoogleLogin();
      } else {
        setError('Google OAuth is not configured. Please set REACT_APP_GOOGLE_CLIENT_ID.');
      }
    } else if (provider === "microsoft") {
      handleMicrosoftLogin();
    } else if (provider === "meta") {
      handleMetaLogin();
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>{isRegister ? "Register" : "Login"}</h2>
        
        {/* OAuth Buttons */}
        <div className="oauth-buttons" style={{ marginBottom: "20px" }}>
          {googleClientId && (
            <button
              type="button"
              className="oauth-button google"
              onClick={() => handleOAuth("google")}
              disabled={loading || oauthLoading}
              style={{
                width: "100%",
                padding: "10px",
                marginBottom: "10px",
                backgroundColor: "#4285F4",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                fontSize: "14px"
              }}
            >
              {oauthLoading === "google" ? "Loading..." : "Continue with Google"}
            </button>
          )}
          <button
            type="button"
            className="oauth-button microsoft"
            onClick={() => handleOAuth("microsoft")}
            disabled={loading || oauthLoading}
            style={{
              width: "100%",
              padding: "10px",
              marginBottom: "10px",
              backgroundColor: "#0078D4",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "14px"
            }}
          >
            {oauthLoading === "microsoft" ? "Loading..." : "Continue with Microsoft"}
          </button>
          <button
            type="button"
            className="oauth-button meta"
            onClick={() => handleOAuth("meta")}
            disabled={loading || oauthLoading}
            style={{
              width: "100%",
              padding: "10px",
              marginBottom: "10px",
              backgroundColor: "#1877F2",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "14px"
            }}
          >
            {oauthLoading === "meta" ? "Loading..." : "Continue with Meta"}
          </button>
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

