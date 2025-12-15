// frontend/src/services/auth.js
import { API_BASE } from "../config/api";

export const authService = {
  getToken() {
    return localStorage.getItem("token");
  },

  setToken(token) {
    localStorage.setItem("token", token);
  },

  removeToken() {
    localStorage.removeItem("token");
  },

  getAuthHeaders() {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  async register(username, password, bggId) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, bgg_id: bggId || null }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Registration failed");
    }
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  },

  async login(username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Login failed");
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
  },
};

