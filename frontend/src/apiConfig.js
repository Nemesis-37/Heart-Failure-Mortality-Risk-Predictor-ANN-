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

let _inFlightRefreshPromise = null

/**
 * Single-flight refresh of expired short-lived JWT access token using refresh_token.
 * Returns the new access_token string or null if refresh fails/unavailable.
 */
export async function refreshAccessToken() {
  if (_inFlightRefreshPromise) return _inFlightRefreshPromise

  _inFlightRefreshPromise = (async () => {
    try {
      const refreshToken = localStorage.getItem('cardiopredict_refresh_token')
      if (!refreshToken) return null

      const res = await fetch(apiUrl('/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      const ct = res.headers.get('content-type') || ''
      if (!res.ok || !ct.includes('application/json')) {
        return null
      }
      const data = await res.json()
      if (data && data.access_token) {
        localStorage.setItem('cardiopredict_access_token', data.access_token)
        if (data.refresh_token) {
          localStorage.setItem('cardiopredict_refresh_token', data.refresh_token)
        }
        return data.access_token
      }
      return null
    } catch {
      return null
    } finally {
      _inFlightRefreshPromise = null
    }
  })()

  return _inFlightRefreshPromise
}

/**
 * Authenticated fetch wrapper:
 * - Attaches Bearer token from localStorage
 * - On HTTP 401, refreshes access token via /auth/refresh once and retries
 * - Dispatches 'cardiopredict:session-expired' if refresh fails
 */
export async function authorizedFetch(path, options = {}) {
  const token = localStorage.getItem('cardiopredict_access_token')
  const headers = {
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }

  let res = await fetch(apiUrl(path), { ...options, headers })

  if (res.status === 401) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      const retryHeaders = {
        ...(options.headers || {}),
        Authorization: `Bearer ${newToken}`,
      }
      res = await fetch(apiUrl(path), { ...options, headers: retryHeaders })
    }
    if (res.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('cardiopredict:session-expired'))
    }
  }

  return res
}

export default API_BASE_URL
