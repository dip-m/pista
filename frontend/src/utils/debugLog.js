// Debug logging helper (logs to both HTTP endpoint and console for Android adb logcat)
export const debugLog = (location, message, data, hypothesisId) => {
  const logData = {location,message,data,timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId};
  console.log(`[DEBUG] ${location}: ${message}`, data); // For adb logcat
  try {
    fetch('http://127.0.0.1:7243/ingest/b6bed85f-e596-4cd0-842c-919c411babb2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData)}).catch(()=>{});
  } catch(e) {}
};

export const debugError = (location, message, error, hypothesisId) => {
  const logData = {location,message,data:{error:error?.message||error,stack:error?.stack},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId};
  console.error(`[DEBUG ERROR] ${location}: ${message}`, error); // For adb logcat
  try {
    fetch('http://127.0.0.1:7243/ingest/b6bed85f-e596-4cd0-842c-919c411babb2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logData)}).catch(()=>{});
  } catch(e) {}
};
