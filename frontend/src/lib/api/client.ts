/**
 * API Client
 * Centralized HTTP client using fetch with type safety
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

interface RequestConfig extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * Validation error from backend (field-level error).
 */
interface ValidationError {
  field: string;
  message: string;
  value?: unknown;
}

/**
 * Structured error from backend API.
 */
interface BackendError {
  status: 'error';
  error?: {
    type: string;
    message: string;
    detail?: string | null;
    code?: string | null;
  };
  errors?: ValidationError[];
  metadata?: {
    timestamp: string;
    request_id?: string | null;
  };
}

/**
 * API error with status code and parsed backend error data.
 */
interface ApiError extends Error {
  status: number;
  data?: unknown;
  /** Validation errors if this was a 422 response */
  validationErrors?: ValidationError[];
  /** Error type from backend */
  errorType?: string;
}

/**
 * Check if the error data matches the backend error response structure.
 */
function isBackendError(data: unknown): data is BackendError {
  return (
    typeof data === 'object' &&
    data !== null &&
    'status' in data &&
    (data as BackendError).status === 'error'
  );
}

/**
 * Create a structured API error from response data.
 *
 * Handles the Novel Engine backend error format:
 * - `error.message` for the main error message
 * - `errors` array for validation errors (422 responses)
 * - Falls back to `detail` for simple error messages
 */
function createApiError(message: string, status: number, data?: unknown): ApiError {
  const error = new Error(message) as ApiError;
  error.status = status;
  error.data = data;

  // Extract structured error information from backend response
  if (isBackendError(data)) {
    if (data.error?.type) {
      error.errorType = data.error.type;
    }
    if (data.errors && data.errors.length > 0) {
      error.validationErrors = data.errors;
    }
  }

  return error;
}

function buildUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined>
): string {
  const url = new URL(path, window.location.origin);

  if (!path.startsWith('http')) {
    url.pathname = `${API_BASE_URL}${path}`;
  }

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

/**
 * Extract a human-readable error message from backend response.
 *
 * Priority:
 * 1. `error.message` (structured Novel Engine error)
 * 2. `detail` (FastAPI HTTPException)
 * 3. Fallback to HTTP status
 */
function extractErrorMessage(errorData: unknown, status: number): string {
  if (isBackendError(errorData)) {
    // For validation errors, summarize the field errors
    if (errorData.errors && errorData.errors.length > 0) {
      const fieldErrors = errorData.errors
        .map((e) => `${e.field}: ${e.message}`)
        .join('; ');
      return `Validation failed: ${fieldErrors}`;
    }
    // Use main error message
    if (errorData.error?.message) {
      return errorData.error.message;
    }
  }

  // Fallback: check for simple 'detail' field (FastAPI HTTPException)
  if (typeof errorData === 'object' && errorData !== null && 'detail' in errorData) {
    return String((errorData as { detail: unknown }).detail);
  }

  return `HTTP ${status}`;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }

    const message = extractErrorMessage(errorData, response.status);
    throw createApiError(message, response.status, errorData);
  }

  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    return {} as T;
  }

  return response.json();
}

function getAuthHeader(): Record<string, string> {
  const authData = localStorage.getItem('novel-engine-auth');
  if (authData) {
    try {
      const parsed = JSON.parse(authData);
      if (parsed.state?.token?.accessToken) {
        return { Authorization: `Bearer ${parsed.state.token.accessToken}` };
      }
    } catch {
      // Invalid stored data
    }
  }
  return {};
}

export const api = {
  async get<T>(path: string, config?: RequestConfig): Promise<T> {
    const url = buildUrl(path, config?.params);
    const response = await fetch(url, {
      ...config,
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
        ...config?.headers,
      },
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, data?: unknown, config?: RequestConfig): Promise<T> {
    const url = buildUrl(path, config?.params);
    const response = await fetch(url, {
      ...config,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
        ...config?.headers,
      },
      ...(data !== undefined ? { body: JSON.stringify(data) } : {}),
    });
    return handleResponse<T>(response);
  },

  async put<T>(path: string, data?: unknown, config?: RequestConfig): Promise<T> {
    const url = buildUrl(path, config?.params);
    const response = await fetch(url, {
      ...config,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
        ...config?.headers,
      },
      ...(data !== undefined ? { body: JSON.stringify(data) } : {}),
    });
    return handleResponse<T>(response);
  },

  async patch<T>(path: string, data?: unknown, config?: RequestConfig): Promise<T> {
    const url = buildUrl(path, config?.params);
    const response = await fetch(url, {
      ...config,
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
        ...config?.headers,
      },
      ...(data !== undefined ? { body: JSON.stringify(data) } : {}),
    });
    return handleResponse<T>(response);
  },

  async delete<T>(path: string, config?: RequestConfig): Promise<T> {
    const url = buildUrl(path, config?.params);
    const response = await fetch(url, {
      ...config,
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
        ...config?.headers,
      },
    });
    return handleResponse<T>(response);
  },
};

export type { ApiError, ValidationError, BackendError };
