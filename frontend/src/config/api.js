// API configuration
// Use environment variable or default to localhost for development
export const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const apiConfig = {
  API_BASE,
};

export default apiConfig;
