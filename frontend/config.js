// src/config.js
// This will look for the environment variable, or default to localhost
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";