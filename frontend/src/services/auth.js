// frontend/src/services/auth.js
import { API_BASE } from "../config/api";

export const authService = {
  getToken() {
    return localStorage.getItem("token");
  },

  setToken(token, rememberMe = false) {
    if (rememberMe) {
      // Store token with longer expiration (30 days)
      localStorage.setItem("token", token);
      localStorage.setItem("token_expires", (Date.now() + 30 * 24 * 60 * 60 * 1000).toString());
    } else {
      // Store token with session expiration (24 hours)
      localStorage.setItem("token", token);
      localStorage.setItem("token_expires", (Date.now() + 24 * 60 * 60 * 1000).toString());
    }
  },

  isTokenExpired() {
    const expires = localStorage.getItem("token_expires");
    if (!expires) return true;
    return Date.now() > parseInt(expires, 10);
  },

  removeToken() {
    localStorage.removeItem("token");
  },

  getAuthHeaders() {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  async register(email, password, rememberMe = false) {
    const res = await fetch(`${API_BASE}/auth/email/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Registration failed");
    }
    const data = await res.json();
    this.setToken(data.access_token, rememberMe);
    return data;
  },

  async login(email, password, rememberMe = false) {
    const res = await fetch(`${API_BASE}/auth/email/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Login failed");
    }
    const data = await res.json();
    this.setToken(data.access_token, rememberMe);
    return data;
  },

  async oauthCallback(provider, token, email = null, name = null) {
    const res = await fetch(`${API_BASE}/auth/oauth/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider,
        token,
        email,
        name
      }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "OAuth authentication failed");
    }
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  },

  async getCurrentUser() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: this.getAuthHeaders(),
    });
    if (!res.ok) {
      return null;
    }
    return await res.json();
  },

  logout() {
    this.removeToken();
    localStorage.removeItem("token_expires");
  },
};
