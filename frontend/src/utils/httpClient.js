// HTTP client that uses Capacitor HTTP on mobile to bypass CORS
import { CapacitorHttp, Capacitor } from '@capacitor/core';

const isCapacitor = Capacitor.isNativePlatform();

/**
 * HTTP client that bypasses CORS on mobile by using Capacitor's native HTTP
 */
export async function httpRequest(url, options = {}) {
  // #region agent log
  console.log('[DEBUG] httpClient:httpRequest - Request starting', {url,method:options.method||'GET',isCapacitor,hasCapacitorHttp:!!CapacitorHttp});
  fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'httpClient.js:httpRequest',message:'Request starting',data:{url,method:options.method||'GET',isCapacitor,hasCapacitorHttp:!!CapacitorHttp},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion

  if (isCapacitor && CapacitorHttp) {
    // Use Capacitor HTTP on mobile to bypass CORS
    try {
      // #region agent log
      console.log('[DEBUG] httpClient:httpRequest - Using Capacitor HTTP', {url});
      fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'httpClient.js:httpRequest',message:'Using Capacitor HTTP',data:{url},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion

      // Parse body if it's a string (JSON)
      let requestData = options.body;
      if (typeof requestData === 'string') {
        try {
          requestData = JSON.parse(requestData);
        } catch (e) {
          // Keep as string if not JSON
        }
      }

      const response = await CapacitorHttp.request({
        url,
        method: options.method || 'GET',
        headers: options.headers || {},
        data: requestData,
      });

      // #region agent log
      console.log('[DEBUG] httpClient:httpRequest - Capacitor HTTP response', {status:response.status,statusText:response.statusText});
      fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'httpClient.js:httpRequest',message:'Capacitor HTTP response',data:{status:response.status,statusText:response.statusText},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion

      // Convert Capacitor response to fetch-like response
      return {
        ok: response.status >= 200 && response.status < 300,
        status: response.status,
        statusText: response.statusText || '',
        json: async () => {
          if (typeof response.data === 'string') {
            return JSON.parse(response.data);
          }
          return response.data;
        },
        text: async () => {
          if (typeof response.data === 'string') {
            return response.data;
          }
          return JSON.stringify(response.data);
        },
        headers: new Headers(response.headers || {}),
      };
    } catch (error) {
      // #region agent log
      console.log('[DEBUG] httpClient:httpRequest - Capacitor HTTP error', {error:error.message});
      fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'httpClient.js:httpRequest',message:'Capacitor HTTP error',data:{error:error.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      throw error;
    }
  } else {
    // Use standard fetch on web
    // #region agent log
    console.log('[DEBUG] httpClient:httpRequest - Using standard fetch', {url});
    fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'httpClient.js:httpRequest',message:'Using standard fetch',data:{url},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
    // #endregion
    return fetch(url, options);
  }
}
