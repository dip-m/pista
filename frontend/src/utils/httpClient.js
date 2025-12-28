// HTTP client that uses Capacitor HTTP on mobile to bypass CORS
import { CapacitorHttp, Capacitor } from '@capacitor/core';

const isCapacitor = Capacitor.isNativePlatform();

/**
 * HTTP client that bypasses CORS on mobile by using Capacitor's native HTTP
 */
export async function httpRequest(url, options = {}) {
  if (isCapacitor && CapacitorHttp) {
    // Use Capacitor HTTP on mobile to bypass CORS
    try {

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
      throw error;
    }
  } else {
    // Use standard fetch on web
    return fetch(url, options);
  }
}
