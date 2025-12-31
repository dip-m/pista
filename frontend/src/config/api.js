// API configuration
// Use environment variable or default based on platform
const getDefaultApiBase = () => {
  // Check if running on Capacitor native platform (mobile app)
  // We need to check this way because importing Capacitor sets window.Capacitor even in browser
  let isNativePlatform = false;
  try {
    // Only check if Capacitor is available and we're actually on a native platform
    if (typeof window !== 'undefined' && window.Capacitor) {
      // Use Capacitor.isNativePlatform() to properly detect native platform
      // This returns true only on actual mobile devices, not in browser
      isNativePlatform = window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform();
    }
  } catch (e) {
    // If Capacitor check fails, assume we're in browser
    isNativePlatform = false;
  }

  if (isNativePlatform) {
    // Mobile app ALWAYS uses production server URL
    // This ensures mobile builds always connect to production, regardless of build environment
    const PRODUCTION_API_URL = "https://web-production-f74f5.up.railway.app";
    return PRODUCTION_API_URL;
  }

  // Web/development - use environment variable or default to localhost
  return process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
};

export const API_BASE = getDefaultApiBase();

const apiConfig = {
  API_BASE,
};

export default apiConfig;
