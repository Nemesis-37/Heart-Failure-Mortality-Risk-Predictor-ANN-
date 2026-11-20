/**
 * Centralized API configuration for Heart Failure Mortality Risk Predictor
 * 
 * In production (unified Render deployment):
 *   Defaults to empty string ('') so all requests use relative paths (e.g. /api/predict, /auth/login)
 *   hitting the same origin without CORS or localhost issues.
 * 
 * In development (Vite):
 *   Vite dev proxy (vite.config.js) forwards /api, /auth, /admin, /predict to http://127.0.0.1:8000.
 * 
 * In custom multi-service deployments:
 *   Override by setting VITE_API_URL in your environment.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export function apiUrl(path = '') {
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath
}

export default API_BASE_URL
