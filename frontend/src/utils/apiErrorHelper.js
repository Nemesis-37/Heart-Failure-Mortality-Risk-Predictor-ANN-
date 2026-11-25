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
 */
export async function safeParseResponse(res) {
  if (!res) return { data: null, text: '' }
  try {
    const text = await res.text()
    try {
      const data = JSON.parse(text)
      return { data, text }
    } catch {
      return { data: null, text }
    }
  } catch (err) {
    return { data: null, text: '' }
  }
}

/**
 * Extract human-readable field errors from Pydantic 422 / FastAPI 400 error payloads.
 */
export function extractFieldErrors(errorData) {
  const fieldErrors = {}
  if (!errorData) return fieldErrors

  // Handle Pydantic v2 validation error array: detail = [{ loc: ['body', 'field'], msg: '...' }]
  if (Array.isArray(errorData.detail)) {
    errorData.detail.forEach((item) => {
      if (item && item.loc && item.loc.length > 0) {
        const fieldName = item.loc[item.loc.length - 1]
        // Clean up Pydantic error strings (e.g. 'Value error, ...' -> '...')
        const cleanMsg = (item.msg || 'Invalid value').replace(/^Value error,\s*/i, '')
        fieldErrors[fieldName] = cleanMsg
      }
    })
  } else if (typeof errorData.detail === 'string') {
    // Check if the detail string mentions a specific known field
    const detailLower = errorData.detail.toLowerCase()
    if (detailLower.includes('email')) {
      fieldErrors.email = errorData.detail
    } else if (detailLower.includes('registration number') || detailLower.includes('registration_number')) {
      fieldErrors.registrationNumber = errorData.detail
    } else if (detailLower.includes('password')) {
      fieldErrors.password = errorData.detail
    } else if (detailLower.includes('patient reference') || detailLower.includes('patient_reference')) {
      fieldErrors.patientRef = errorData.detail
    }
  }

  return fieldErrors
}

/**
 * Parses fetch errors and HTTP response failures into structured, empathetic clinical messages.
 */
export function parseApiError(error, response = null, responseBody = null) {
  const isDev = Boolean(import.meta.env?.DEV)

  // Safe developer logging (strip any sensitive payload data)
  if (isDev) {
    console.debug('[apiErrorHelper] Analyzing API error:', {
      name: error?.name,
      message: error?.message,
      status: response?.status,
      body: responseBody,
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
    const fieldErrors = extractFieldErrors(responseBody)
    const detailMsg = typeof responseBody?.detail === 'string' ? responseBody.detail : ''

    // 400 Bad Request / 422 Unprocessable Entity
    if (status === 400 || status === 422) {
      const summaryMsg =
        detailMsg ||
        (Object.keys(fieldErrors).length > 0
          ? `Please review the highlighted input fields: ${Object.values(fieldErrors).join('; ')}`
          : 'Invalid data format or out-of-range clinical parameters provided.')

      return {
        type: ErrorTypes.VALIDATION_ERROR,
        status,
        message: summaryMsg,
        fieldErrors,
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
