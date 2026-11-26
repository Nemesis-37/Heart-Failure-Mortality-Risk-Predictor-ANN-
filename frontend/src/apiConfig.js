/**
 * Centralized API configuration for Heart Failure Mortality Risk Predictor
 * 
 * Production (Unified Render Deployment):
 *   - The React frontend is served directly by the FastAPI backend on the same origin.
 *   - Relative paths ('/predict', '/api/predict', '/auth/login', etc.) hit the same host seamlessly
 *     without CORS rejections or cross-origin latency.
 *   - SAFETY GUARD: If VITE_API_URL was inadvertently set to a localhost URL in a cloud deployment,
 *     it is safely ignored so the browser never attempts to connect to localhost:8000.
 * 
 * Development (Vite Dev Server on port 5173):
 *   - Vite proxy forwards /api, /auth, /admin, /predict, /health to http://127.0.0.1:8000.
 *   - When on localhost/127.0.0.1, direct fallbacks to http://127.0.0.1:8000 are provided
 *     if the Vite proxy ever drops or encounters an issue.
 */

export const PRODUCTION_RENDER_BACKEND = 'https://heart-failure-mortality-risk-predictor-mfet.onrender.com'

function resolveApiBaseUrl() {
  const envUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/$/, '')

  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname
    const isLocalhost =
      hostname === 'localhost' ||
      hostname === '127.0.0.1' ||
      hostname === '0.0.0.0' ||
      hostname === '::1'

    // If deployed on a live domain (e.g., *.onrender.com or a custom domain)
    // and envUrl erroneously targets localhost, discard it to prevent "Connection refused".
    if (!isLocalhost && envUrl && (envUrl.includes('localhost') || envUrl.includes('127.0.0.1'))) {
      if (import.meta.env.DEV) {
        console.warn('[apiConfig] Overriding localhost VITE_API_URL on non-localhost host:', envUrl)
      }
      return PRODUCTION_RENDER_BACKEND
    }

    // If deployed on Render static site without an environment variable configured,
    // automatically target the canonical deployed Render FastAPI backend service.
    if (!isLocalhost && !envUrl && hostname.includes('onrender.com')) {
      return PRODUCTION_RENDER_BACKEND
    }
  }

  return envUrl
}

export const API_BASE_URL = resolveApiBaseUrl()

/**
 * Returns a normalized URL for a given path using the resolved base URL.
 */
export function apiUrl(path = '') {
  if (!path) return ''
  if (
    path.startsWith('http://') ||
    path.startsWith('https://') ||
    path.startsWith('data:') ||
    path.startsWith('blob:')
  ) {
    return path
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath
}

/**
 * Returns ordered candidate endpoints for prediction requests.
 * Evaluates both root and /api prefixed routes, and on localhost includes direct 127.0.0.1 fallbacks.
 */
export function getPredictionCandidateUrls(modelId = 'lr') {
  const isAnn = modelId === 'ann'
  const primarySlug = isAnn ? '/predict-ann' : '/predict'
  const apiSlug = isAnn ? '/api/predict-ann' : '/api/predict'

  const candidates = [
    apiUrl(primarySlug),
    apiUrl(apiSlug),
  ]

  // Add direct local port fallbacks ONLY when running on a local developer browser
  if (typeof window !== 'undefined' && window.location) {
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1'

    if (isLocalhost && !API_BASE_URL) {
      candidates.push(`http://127.0.0.1:8000${primarySlug}`)
      candidates.push(`http://localhost:8000${primarySlug}`)
      candidates.push(`http://127.0.0.1:8000${apiSlug}`)
    }
  }

  return [...new Set(candidates.filter(Boolean))]
}

/**
 * Returns ordered candidate endpoints for authentication requests.
 */
export function getAuthCandidateUrls(actionSlug = '/auth/register') {
  const clean = actionSlug.startsWith('/') ? actionSlug : `/${actionSlug}`
  const apiVariant = clean.startsWith('/api') ? clean : `/api${clean}`

  const candidates = [
    apiUrl(clean),
    apiUrl(apiVariant),
  ]

  if (typeof window !== 'undefined' && window.location) {
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1'

    if (isLocalhost && !API_BASE_URL) {
      candidates.push(`http://127.0.0.1:8000${clean}`)
      candidates.push(`http://localhost:8000${clean}`)
    }
  }

  return [...new Set(candidates.filter(Boolean))]
}

/**
 * Returns ordered candidate endpoints for health probe checks.
 */
export function getHealthCandidateUrls() {
  const candidates = [
    apiUrl('/health'),
    apiUrl('/api/health'),
  ]

  if (typeof window !== 'undefined' && window.location) {
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1'

    if (isLocalhost && !API_BASE_URL) {
      candidates.push('http://127.0.0.1:8000/health')
    }
  }

  return [...new Set(candidates.filter(Boolean))]
}

export default API_BASE_URL
