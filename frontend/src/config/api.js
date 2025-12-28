// API configuration
// Use environment variable or default based on platform
const getDefaultApiBase = () => {
  // Check if running on Capacitor (mobile)
  const isCapacitor = window.Capacitor !== undefined;

  if (isCapacitor) {
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
