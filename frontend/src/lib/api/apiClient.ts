import axios from 'axios';
import type {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosRequestHeaders,
  AxiosResponse,
} from 'axios';
import { store } from '@/store/store';
import { refreshUserToken, logoutUser } from '@/store/slices/authSlice';
import { logger } from '@/services/logging/LoggerFactory';
import type { IAuthenticationService } from '@/services/auth/IAuthenticationService';
import { normalizeApiError } from './errors';
import config from '@/config/env';

export const ApiClientConstants = {
  CLIENT_IDENTIFIER: 'novel-engine-frontend',
  DEFAULT_MAX_ATTEMPTS: 3,
  BACKOFF_BASE_MS: 200,
  MAX_BACKOFF_MS: 2000,
} as const;

const IDEMPOTENT_METHODS = new Set(['get', 'head', 'options']);
const MUTATION_METHODS = new Set(['post', 'put', 'patch', 'delete']);

export interface ApiRequestMetadata {
  startTime?: number;
  correlationId?: string;
  attemptCount?: number;
  maxAttempts?: number;
  allowMutationRetry?: boolean;
}

export interface BaseAPIResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
    recoverable: boolean;
  };
  metadata?: {
    timestamp: string;
    request_id: string;
    version?: string;
    rate_limit?: {
      remaining: number;
      reset_time: string;
    };
  };
}

declare module 'axios' {
  interface AxiosRequestConfig {
    metadata?: ApiRequestMetadata;
    _retry?: boolean;
  }
}

type RetryableRequestConfig = AxiosRequestConfig & { _retry?: boolean };

const generateRequestId = (): string =>
  `req_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;

const getCsrfTokenFromCookie = (): string | null => {
  if (typeof document === 'undefined') return null;
  return (
    document.cookie
      .split('; ')
      .find((row) => row.startsWith('csrf_token='))
      ?.split('=')[1] ?? null
  );
};

const toNonEmptyString = (value?: unknown): string | undefined => {
  if (typeof value !== 'string') return undefined;
  const trimmed = value.trim();
  return trimmed.length ? trimmed : undefined;
};

const extractCorrelationIdFromHeaders = (headers?: Record<string, string | undefined>): string | undefined => {
  if (!headers) return undefined;
  for (const key of ['x-correlation-id', 'X-Request-ID', 'x-request-id']) {
    const candidate = toNonEmptyString(headers[key]);
    if (candidate) return candidate;
  }
  return undefined;
};

const isIdempotentMethod = (method?: string): boolean => !!method && IDEMPOTENT_METHODS.has(method.toLowerCase());

const isMutationMethod = (method?: string): boolean => !!method && MUTATION_METHODS.has(method.toLowerCase());

const hasIdempotencyHeader = (headers?: AxiosRequestHeaders | Record<string, unknown>): boolean => {
  if (!headers) return false;
  return [
    headers['idempotency-key'],
    headers['x-idempotency-key'],
    headers['Idempotency-Key'],
    headers['X-Idempotency-Key'],
  ].some((value) => !!toNonEmptyString(value));
};

export const getRetryDelayMs = (attempt: number): number => {
  const normalized = Math.max(1, attempt);
  return Math.min(ApiClientConstants.MAX_BACKOFF_MS, ApiClientConstants.BACKOFF_BASE_MS * 2 ** (normalized - 1));
};

const isRetryableStatus = (status?: number): boolean => {
  if (status === undefined) return false;
  if (status === 408 || status === 429) return true;
  return status >= 500;
};

const isNetworkError = (error: AxiosError): boolean => !error.response;

export const shouldAutoRetryRequest = (config: AxiosRequestConfig, error: AxiosError): boolean => {
  const metadata = config.metadata;
  const attemptCount = metadata?.attemptCount ?? 1;
  const maxAttempts = metadata?.maxAttempts ?? ApiClientConstants.DEFAULT_MAX_ATTEMPTS;

  if (attemptCount >= maxAttempts) return false;
  if (error.response?.status === 401) return false;

  const retryableStatus = isRetryableStatus(error.response?.status) || isNetworkError(error);
  if (!retryableStatus) return false;

  const method = config.method?.toLowerCase();
  if (method && isMutationMethod(method)) {
    return Boolean(metadata?.allowMutationRetry) || hasIdempotencyHeader(config.headers as Record<string, unknown>);
  }

  if (method && !isIdempotentMethod(method)) return false;
  return true;
};

const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

const logRequest = (config: AxiosRequestConfig, status?: number, success = true, error?: AxiosError): void => {
  const metadata = config.metadata;
  const durationMs = metadata?.startTime ? Math.max(Date.now() - metadata.startTime, 0) : undefined;
  const context = {
    component: 'apiClient',
    method: config.method,
    url: config.url,
    status,
    attempts: metadata?.attemptCount,
    durationMs,
    correlationId: metadata?.correlationId,
  };
  if (success) {
    logger.info('API request completed', context);
  } else {
    logger.error('API request failed', error, context);
  }
};

export const createHttpClient = (options: AxiosRequestConfig = {}): AxiosInstance => {
  return axios.create({
    baseURL: options.baseURL ?? (config.apiBaseUrl || '/'),
    timeout: options.timeout ?? config.apiTimeout,
    withCredentials: true,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  });
};

export const createAPIClient = (authService?: IAuthenticationService): AxiosInstance => {
  const client = createHttpClient();

  client.interceptors.request.use(
    (config) => {
      if (!config.headers) {
        config.headers = {} as AxiosRequestHeaders;
      }
      const headers = config.headers as AxiosRequestHeaders;

      if (authService) {
        const token = authService.getToken();
        if (token) {
          headers.Authorization = `${token.tokenType} ${token.accessToken}`;
        }
      } else {
        const state = store.getState();
        const token = state.auth.accessToken;
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }
      }

      const method = config.method?.toLowerCase();
      if (method && ['post', 'put', 'delete', 'patch'].includes(method)) {
        const csrfToken = getCsrfTokenFromCookie();
        if (csrfToken) {
          headers['X-CSRF-Token'] = csrfToken;
        }
      }

      const now = Date.now();
      const metadata = (config.metadata ?? {}) as ApiRequestMetadata;
      metadata.maxAttempts ??= ApiClientConstants.DEFAULT_MAX_ATTEMPTS;
      metadata.startTime ??= now;
      metadata.attemptCount = (metadata.attemptCount ?? 0) + 1;
      metadata.correlationId ??= generateRequestId();
      config.metadata = metadata;

      const durationSoFar = Math.max(now - metadata.startTime, 0);
      headers['X-Request-ID'] = metadata.correlationId;
      headers['X-Correlation-ID'] = metadata.correlationId;
      headers['X-Client'] = ApiClientConstants.CLIENT_IDENTIFIER;
      headers['X-Attempt'] = String(metadata.attemptCount);
      headers['X-Request-Duration'] = String(durationSoFar);

      return config;
    },
    (error) => Promise.reject(error)
  );

  client.interceptors.response.use(
    (response: AxiosResponse) => {
      const metadata = response.config.metadata;
      if (metadata) {
        const serverCorrelationId = extractCorrelationIdFromHeaders(response.headers as Record<string, string | undefined>);
        if (serverCorrelationId) {
          metadata.correlationId = serverCorrelationId;
        }
      }
      logRequest(response.config, response.status, true);
      return response;
    },
    async (error: AxiosError) => {
      const originalRequest = error.config as RetryableRequestConfig | undefined;
      if (!originalRequest) {
        return Promise.reject(normalizeApiError(error));
      }

      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;
        try {
          if (authService) {
            const newToken = await authService.refreshToken();
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `${newToken.tokenType} ${newToken.accessToken}`;
            }
          } else {
            await store.dispatch(refreshUserToken());
            const state = store.getState();
            if (state.auth.accessToken && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${state.auth.accessToken}`;
            }
          }
          return client(originalRequest);
        } catch (refreshError) {
          logger.error('Token refresh failed, logging out', refreshError as Error);
          if (authService) {
            await authService.logout();
          } else {
            store.dispatch(logoutUser());
          }
          if (typeof window !== 'undefined') window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }

      if (shouldAutoRetryRequest(originalRequest, error)) {
        const attempt = originalRequest.metadata?.attemptCount ?? 1;
        await delay(getRetryDelayMs(attempt));
        return client(originalRequest);
      }

      const serverCorrelationId = extractCorrelationIdFromHeaders(
        (error.response?.headers ?? {}) as Record<string, string | undefined>
      );
      if (serverCorrelationId && originalRequest.metadata) {
        originalRequest.metadata.correlationId = serverCorrelationId;
      }

      logRequest(originalRequest, error.response?.status, false, error);
      return Promise.reject(normalizeApiError(error));
    }
  );

  return client;
};

export const apiClient = createAPIClient();
export const createAuthenticatedAPIClient = (authService: IAuthenticationService) => createAPIClient(authService);

export const handleAPIResponse = <T>(response: AxiosResponse<BaseAPIResponse<T>>): BaseAPIResponse<T> => {
  return response.data;
};

export const handleAPIError = (error: unknown): never => {
  if (error instanceof Error) throw error;
  throw normalizeApiError(error);
};

export default apiClient;
