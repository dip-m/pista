// frontend/src/services/auth.js
import { API_BASE } from "../config/api";
import { httpRequest } from "../utils/httpClient";

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
    const res = await httpRequest(`${API_BASE}/auth/email/register`, {
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
    const loginUrl = `${API_BASE}/auth/email/login`;
    const requestHeaders = { "Content-Type": "application/json" };
    const requestBody = JSON.stringify({ email, password });

    // #region agent log
    console.log('[DEBUG] auth.js:login - Login request starting', {loginUrl,apiBase:API_BASE,urlLength:loginUrl.length,hasTrailingSlash:loginUrl.endsWith('/'),hasDoubleSlash:loginUrl.includes('//'),headers:requestHeaders,bodyLength:requestBody.length});
    fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:login',message:'Login request starting',data:{loginUrl,apiBase:API_BASE,urlLength:loginUrl.length,hasTrailingSlash:loginUrl.endsWith('/'),hasDoubleSlash:loginUrl.includes('//'),headers:requestHeaders,bodyLength:requestBody.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
    // #endregion

    try {
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:login',message:'Before httpRequest call',data:{loginUrl,method:'POST'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion

      const res = await httpRequest(loginUrl, {
        method: "POST",
        headers: requestHeaders,
        body: requestBody,
      });

      // #region agent log
      const responseHeaders = res.headers instanceof Headers ? Object.fromEntries(res.headers.entries()) : res.headers || {};
      console.log('[DEBUG] auth.js:login - HTTP response received', {status:res.status,statusText:res.statusText,ok:res.ok,headers:responseHeaders});
      fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:login',message:'HTTP response received',data:{status:res.status,statusText:res.statusText,ok:res.ok,headers:responseHeaders},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion

      if (!res.ok) {
        let errorData;
        try {
          errorData = await res.json();
        } catch (e) {
          errorData = { detail: `HTTP ${res.status}: ${res.statusText}` };
        }
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:login',message:'Login failed - response not ok',data:{status:res.status,statusText:res.statusText,errorData},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
        // #endregion
        throw new Error(errorData.detail || "Login failed");
      }
      const data = await res.json();
      this.setToken(data.access_token, rememberMe);
      // #region agent log
      fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:login',message:'Login successful',data:{hasToken:!!data.access_token},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      return data;
    } catch (err) {
      // #region agent log
      console.log('[DEBUG] auth.js:login - Login exception caught', {errorName:err.name,errorMessage:err.message,errorStack:err.stack,isNetworkError:err.message.includes('fetch'),isCorsError:err.message.includes('CORS')});
      fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'auth.js:login',message:'Login exception caught',data:{errorName:err.name,errorMessage:err.message,errorStack:err.stack,isNetworkError:err.message.includes('fetch'),isCorsError:err.message.includes('CORS')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
      // #endregion
      throw err;
    }
  },

  async oauthCallback(provider, token, email = null, name = null) {
    const res = await httpRequest(`${API_BASE}/auth/oauth/callback`, {
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
    const res = await httpRequest(`${API_BASE}/auth/me`, {
      method: "GET",
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
