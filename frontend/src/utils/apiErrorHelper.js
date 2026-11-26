/**
 * frontend/src/utils/apiErrorHelper.js
 * ====================================
 * Standardized API error parser and diagnostic utility for CardioPredict.
 * 
 * Classifies network, HTTP, and validation errors into user-friendly clinical messages
 * while preserving detailed technical diagnostic logs strictly in development mode.
 * Never prints passwords, tokens, or sensitive patient values to logs.
 */

export const ErrorTypes = {
  BACKEND_UNAVAILABLE: 'BACKEND_UNAVAILABLE',
  TIMEOUT: 'TIMEOUT',
  CORS_OR_NETWORK: 'CORS_OR_NETWORK',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN: 'UNKNOWN',
}

/**
 * Safely parse JSON from a response, falling back to text if response is HTML or malformed.
 * Returns the parsed JSON object directly, or an object with { detail: text } if non-JSON.
 */
export async function safeParseResponse(res) {
  if (!res) return null
  try {
    const text = await res.text()
    if (!text) return null
    try {
      return JSON.parse(text)
    } catch {
      return { detail: text }
    }
  } catch (err) {
    return null
  }
}

/**
 * Extract human-readable field errors from Pydantic 422 / FastAPI 400 error payloads.
 */
export function extractFieldErrors(errorData) {
  const fieldErrors = {}
  if (!errorData) return fieldErrors

  // Handle nested error payload if passed { data: ... }
  const data = errorData.data !== undefined ? errorData.data : errorData

  // Helper to store both camelCase and snake_case keys so React forms bind reliably
  const setNormalized = (key, msg) => {
    fieldErrors[key] = msg
    const camel = key.replace(/_([a-z])/g, (_, char) => char.toUpperCase())
    fieldErrors[camel] = msg
  }

  // Handle Pydantic v2 validation error array: detail = [{ loc: ['body', 'field'], msg: '...' }]
  if (Array.isArray(data.detail)) {
    data.detail.forEach((item) => {
      if (item && item.loc && item.loc.length > 0) {
        const fieldName = String(item.loc[item.loc.length - 1])
        const cleanMsg = (item.msg || 'Invalid value').replace(/^Value error,\s*/i, '')
        setNormalized(fieldName, cleanMsg)
      }
    })
  } else if (typeof data.detail === 'string') {
    // Check if the detail string mentions a specific known field
    const detailLower = data.detail.toLowerCase()
    if (detailLower.includes('match') || detailLower.includes('confirm')) {
      fieldErrors.confirmPassword = data.detail
    } else if (detailLower.includes('password')) {
      fieldErrors.password = data.detail
    } else if (detailLower.includes('email')) {
      fieldErrors.email = data.detail
    } else if (detailLower.includes('registration number') || detailLower.includes('registration_number')) {
      fieldErrors.registrationNumber = data.detail
    } else if (detailLower.includes('patient reference') || detailLower.includes('patient_reference')) {
      fieldErrors.patientRef = data.detail
    } else if (detailLower.includes('full name') || detailLower.includes('full_name')) {
      fieldErrors.fullName = data.detail
    } else if (detailLower.includes('degree') || detailLower.includes('qualification')) {
      fieldErrors.medicalDegree = data.detail
    } else if (detailLower.includes('council')) {
      fieldErrors.registrationCouncil = data.detail
    } else if (detailLower.includes('contact') || detailLower.includes('phone') || detailLower.includes('mobile')) {
      fieldErrors.mobile = data.detail
    }
  }

  return fieldErrors
}

/**
 * Parses fetch errors and HTTP response failures into structured, empathetic clinical messages.
 */
export function parseApiError(error, response = null, responseBody = null) {
  const isDev = Boolean(import.meta.env?.DEV)
  const actualBody = responseBody?.data !== undefined ? responseBody.data : responseBody

  // Safe developer logging (strip any sensitive payload data)
  if (isDev) {
    console.debug('[apiErrorHelper] Analyzing API error:', {
      name: error?.name,
      message: error?.message,
      status: response?.status,
      body: actualBody,
    })
  }

  // 1. Timeout / Abort errors
  if (error?.name === 'AbortError' || error?.message?.toLowerCase().includes('timeout')) {
    return {
      type: ErrorTypes.TIMEOUT,
      status: 408,
      message: 'The server took too long to respond. If running on Render, the backend service may be waking up from sleep (cold start). Please retry in 15–30 seconds.',
      fieldErrors: {},
      isRetryable: true,
    }
  }

  // 2. HTTP Status Code Errors
  if (response) {
    const status = response.status
    const fieldErrors = extractFieldErrors(actualBody)
    const detailMsg = typeof actualBody?.detail === 'string' ? actualBody.detail : ''

    // 400 Bad Request / 422 Unprocessable Entity
    if (status === 400 || status === 422) {
      const summaryMsg =
        detailMsg ||
        (Object.keys(fieldErrors).length > 0
          ? `Please review the highlighted input fields: ${Object.values(fieldErrors).join('; ')}`
          : 'Validation failed. Please verify that all required fields are correctly formatted.')

      return {
        type: ErrorTypes.VALIDATION_ERROR,
        status,
        message: summaryMsg,
        fieldErrors,
        isRetryable: false,
      }
    }

    // 405 Method Not Allowed
    if (status === 405) {
      return {
        type: ErrorTypes.SERVER_ERROR,
        status,
        message: 'Endpoint method not allowed (405). The server routing module may be reloading. Please refresh and try again.',
        fieldErrors: {},
        isRetryable: false,
      }
    }

    // 401 Unauthorized
    if (status === 401) {
      return {
        type: ErrorTypes.UNAUTHORIZED,
        status,
        message: detailMsg || 'Physician session has expired or authentication credentials are invalid. Please sign in again.',
        fieldErrors,
        isRetryable: false,
      }
    }

    // 403 Forbidden
    if (status === 403) {
      return {
        type: ErrorTypes.FORBIDDEN,
        status,
        message: detailMsg || 'Access restricted. Your physician account may still be awaiting administrative credential verification.',
        fieldErrors,
        isRetryable: false,
      }
    }

    // 429 Too Many Requests
    if (status === 429) {
      return {
        type: ErrorTypes.BACKEND_UNAVAILABLE,
        status,
        message: detailMsg || 'Too many requests were sent in a short window. Please wait a moment before trying again.',
        fieldErrors,
        isRetryable: true,
      }
    }

    // 502 / 503 / 504 Gateway / Service Unavailable
    if (status === 502 || status === 503 || status === 504) {
      return {
        type: ErrorTypes.BACKEND_UNAVAILABLE,
        status,
        message: 'The clinical inference backend is currently starting up or temporarily unavailable. If deployed on Render free tier, please allow 20–45 seconds for container wake-up.',
        fieldErrors: {},
        isRetryable: true,
      }
    }

    // 500 Internal Server Error
    if (status === 500) {
      return {
        type: ErrorTypes.SERVER_ERROR,
        status,
        message: detailMsg || 'The backend encountered an unexpected error processing this clinical vector. Please check input parameters and retry.',
        fieldErrors,
        isRetryable: true,
      }
    }
  }

  // 3. Network / CORS / Fetch Level Failures (TypeError: Failed to fetch)
  const isNetworkFailure =
    !response ||
    error instanceof TypeError ||
    error?.message === 'Failed to fetch' ||
    error?.message?.toLowerCase().includes('network') ||
    error?.message?.toLowerCase().includes('refused')

  if (isNetworkFailure) {
    const isLocalhost =
      typeof window !== 'undefined' &&
      (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')

    const guidance = isLocalhost
      ? 'Ensure the local FastAPI backend server is running (e.g. `python -m uvicorn main:app --host 127.0.0.1 --port 8000`).'
      : 'If running on Render cloud hosting, the instance may be spinning up from sleep mode. Please wait 20–30 seconds and retry.'

    return {
      type: ErrorTypes.BACKEND_UNAVAILABLE,
      status: 0,
      message: `Could not connect to the FastAPI inference server. ${guidance}`,
      fieldErrors: {},
      isRetryable: true,
    }
  }

  // 4. Fallback unknown error
  return {
    type: ErrorTypes.UNKNOWN,
    status: response?.status || 0,
    message: error?.message || 'An unexpected communication error occurred. Please try again.',
    fieldErrors: {},
    isRetryable: true,
  }
}
