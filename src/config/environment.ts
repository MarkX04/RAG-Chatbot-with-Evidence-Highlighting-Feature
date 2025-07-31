// Environment configuration
const isDevelopment = import.meta.env.DEV

// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || (isDevelopment ? 'http://localhost:8000/api' : '/api'),
  TIMEOUT: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  ENABLE_ERROR_REPORTING: import.meta.env.VITE_ENABLE_ERROR_REPORTING === 'true',
}

// AWS Configuration
export const AWS_CONFIG = {
  REGION: import.meta.env.VITE_AWS_REGION || 'us-east-1',
  S3_BUCKET: import.meta.env.VITE_S3_BUCKET || '',
  CLOUDFRONT_DOMAIN: import.meta.env.VITE_CLOUDFRONT_DOMAIN || '',
}

// Application Configuration
export const APP_CONFIG = {
  NAME: import.meta.env.VITE_APP_NAME || 'RAG Chatbot',
  VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
  ENVIRONMENT: import.meta.env.MODE || 'development',
  DEBUG_MODE: import.meta.env.VITE_DEBUG_MODE === 'true',
}

// Feature Flags
export const FEATURE_FLAGS = {
  ENABLE_PDF_HIGHLIGHTING: import.meta.env.VITE_ENABLE_PDF_HIGHLIGHTING === 'true',
  ENABLE_DOCUMENT_UPLOAD: import.meta.env.VITE_ENABLE_DOCUMENT_UPLOAD === 'true',
  MAX_FILE_SIZE: Number(import.meta.env.VITE_MAX_FILE_SIZE) || 10485760, // 10MB default
}

// Feature Flags
export const FEATURES = {
  DEBUG_MODE: isDevelopment,
  ENABLE_LOGGING: isDevelopment,
}

// API Endpoints
export const API_ENDPOINTS = {
  CHAT: `${API_CONFIG.BASE_URL}/chat`,
  UPLOAD: `${API_CONFIG.BASE_URL}/documents/upload`,
  SEARCH: `${API_CONFIG.BASE_URL}/documents/search`,
  HIGHLIGHTED_PDFS: `${API_CONFIG.BASE_URL}/highlighted-pdfs`,
  CLEANUP_PDFS: `${API_CONFIG.BASE_URL}/cleanup-pdfs`,
  HEALTH: `${API_CONFIG.BASE_URL}/health`,
}

// Export individual values for backward compatibility
export const API_BASE_URL = API_CONFIG.BASE_URL
export const config = APP_CONFIG

export default {
  API_CONFIG,
  APP_CONFIG,
  FEATURES,
  API_ENDPOINTS,
}
