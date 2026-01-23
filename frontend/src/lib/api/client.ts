/**
 * API Client
 * Centralized HTTP client using fetch with type safety
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

interface RequestConfig extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

interface ApiError extends Error {
  status: number;
  data?: unknown;
}

function createApiError(message: string, status: number, data?: unknown): ApiError {
  const error = new Error(message) as ApiError;
  error.status = status;
  error.data = data;
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

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }

    const message =
      typeof errorData === 'object' && errorData !== null && 'detail' in errorData
        ? String((errorData as { detail: unknown }).detail)
        : `HTTP ${response.status}`;

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

export type { ApiError };
