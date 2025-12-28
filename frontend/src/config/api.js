// API configuration
// Use environment variable or default based on platform
const getDefaultApiBase = () => {
  // Check if running on Capacitor (mobile)
  const isCapacitor = window.Capacitor !== undefined;

  // #region agent log
  fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.js:getDefaultApiBase',message:'API base determination',data:{isCapacitor,envUrl:process.env.REACT_APP_API_BASE_URL,hasEnvUrl:!!process.env.REACT_APP_API_BASE_URL},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion

  if (isCapacitor) {
    // On Android emulator, use 10.0.2.2 to access host machine
    // On physical device, you need to use your computer's IP address on the local network
    // For production, set REACT_APP_API_BASE_URL to your production API URL
    const apiBase = process.env.REACT_APP_API_BASE_URL || "http://10.0.2.2:8000";
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.js:getDefaultApiBase',message:'Capacitor API base selected',data:{apiBase,isCapacitor:true},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    return apiBase;
  }

  // Web/development - use localhost
  const apiBase = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
  // #region agent log
  fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.js:getDefaultApiBase',message:'Web API base selected',data:{apiBase,isCapacitor:false},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion
  return apiBase;
};

export const API_BASE = getDefaultApiBase();

// #region agent log
console.log('[DEBUG] api.js:export - API_BASE exported', {API_BASE,urlLength:API_BASE.length,hasTrailingSlash:API_BASE.endsWith('/'),hasDoubleHttps:API_BASE.includes('https://https://'),startsWithHttps:API_BASE.startsWith('https://')});
fetch('http://127.0.0.1:7245/ingest/abc48296-4794-49ce-a506-dc4b71ebc651',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.js:export',message:'API_BASE exported',data:{API_BASE,urlLength:API_BASE.length,hasTrailingSlash:API_BASE.endsWith('/'),hasDoubleHttps:API_BASE.includes('https://https://'),startsWithHttps:API_BASE.startsWith('https://')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
// #endregion

const apiConfig = {
  API_BASE,
};

export default apiConfig;
