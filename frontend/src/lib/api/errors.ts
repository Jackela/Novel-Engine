import { isAxiosError } from 'axios';
import type { AxiosRequestConfig } from 'axios';

export type ApiErrorKind = 'network' | 'timeout' | 'auth' | 'validation' | 'http' | 'unknown';

export interface ApiFieldError {
  path: string;
  message: string;
  type?: string;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly code: string;
  readonly status: number | undefined;
  readonly fields: ApiFieldError[] | undefined;
  readonly details: unknown | undefined;
  readonly retryable: boolean;
  readonly correlationId: string | undefined;
  readonly attempts: number | undefined;
  readonly requestDurationMs: number | undefined;
  get recoverable(): boolean {
    return this.retryable;
  }

  constructor(args: {
    message: string;
    kind: ApiErrorKind;
    code: string;
    status?: number | undefined;
    fields?: ApiFieldError[] | undefined;
    details?: unknown;
    retryable: boolean;
    correlationId?: string | undefined;
    attempts?: number | undefined;
    requestDurationMs?: number | undefined;
  }) {
    super(args.message);
    this.name = 'ApiError';
    this.kind = args.kind;
    this.code = args.code;
    this.status = args.status;
    this.fields = args.fields;
    this.details = args.details;
    this.retryable = args.retryable;
    this.correlationId = args.correlationId;
    this.attempts = args.attempts;
    this.requestDurationMs = args.requestDurationMs;
  }
}

type BackendErrorEnvelope = {
  error?: unknown;
  detail?: unknown;
  code?: unknown;
  fields?: unknown;
  retryable?: unknown;
  correlation_id?: unknown;
  message?: unknown;
};

type FastApiValidationError = {
  loc?: unknown;
  msg?: unknown;
  type?: unknown;
};

const asNonEmptyString = (value: unknown): string | undefined =>
  typeof value === 'string' && value.trim() ? value : undefined;

const normalizeValidationFields = (value: unknown): ApiFieldError[] | undefined => {
  if (!Array.isArray(value) || value.length === 0) return undefined;

  const fields = value
    .map((item): ApiFieldError | null => {
      if (!item || typeof item !== 'object') return null;

      const record = item as Record<string, unknown>;
      const path = asNonEmptyString(record.path) ?? asNonEmptyString(record.field);
      const message = asNonEmptyString(record.message) ?? asNonEmptyString(record.msg);
      const type = asNonEmptyString(record.type);

      if (!path || !message) return null;
      return { path, message, ...(type ? { type } : {}) };
    })
    .filter((f): f is ApiFieldError => !!f);

  return fields.length > 0 ? fields : undefined;
};

const normalizeFastApiValidation = (detail: unknown): ApiFieldError[] | undefined => {
  if (!Array.isArray(detail) || detail.length === 0) return undefined;

  const fields = detail
    .map((entry): ApiFieldError | null => {
      const item = entry as FastApiValidationError | null | undefined;
      if (!item || typeof item !== 'object') return null;

      const loc = Array.isArray(item.loc) ? item.loc : [];
      const path = loc
        .map((segment) => (typeof segment === 'string' || typeof segment === 'number' ? String(segment) : ''))
        .filter(Boolean)
        .join('.');

      const message = asNonEmptyString(item.msg);
      const type = asNonEmptyString(item.type);

      if (!path || !message) return null;
      return { path, message, ...(type ? { type } : {}) };
    })
    .filter((f): f is ApiFieldError => !!f);

  return fields.length > 0 ? fields : undefined;
};

type AxiosMetadata = {
  startTime?: number;
  correlationId?: string;
  attemptCount?: number;
};

const getAxiosMetadata = (config: AxiosRequestConfig | undefined): AxiosMetadata | undefined =>
  (config?.metadata as AxiosMetadata | undefined) ?? undefined;

const getApiErrorCode = (data: BackendErrorEnvelope | undefined, status: number): string =>
  asNonEmptyString(data?.code) ??
  asNonEmptyString((data?.error as Record<string, unknown> | undefined)?.code) ??
  `HTTP_${status}`;

const getApiErrorMessage = (data: BackendErrorEnvelope | undefined, fallback: string): string => {
  const detailText = asNonEmptyString(data?.detail);
  const errorText = asNonEmptyString(data?.error);
  const messageText = asNonEmptyString((data as Record<string, unknown> | undefined)?.message);

  return detailText ?? messageText ?? errorText ?? fallback ?? 'Request failed';
};

const getApiErrorFields = (data: BackendErrorEnvelope | undefined): ApiFieldError[] | undefined => {
  const record = data as Record<string, unknown> | undefined;
  return normalizeValidationFields(data?.fields) ?? normalizeFastApiValidation(record?.detail);
};

const getApiErrorKind = (status: number): ApiErrorKind => {
  if (status === 401 || status === 403) {
    return 'auth';
  }

  if (status === 422) {
    return 'validation';
  }

  return 'http';
};

const getRetryable = (status: number, data: BackendErrorEnvelope | undefined): boolean => {
  const retryable = status === 408 || status === 429 || status >= 500;
  const serverRetryable = typeof data?.retryable === 'boolean' ? data.retryable : undefined;
  return serverRetryable ?? retryable;
};

const getHeaderValue = (
  headers: Record<string, string | undefined>,
  keys: string[]
): string | undefined => {
  for (const key of keys) {
    const value = asNonEmptyString(headers[key]);
    if (value) {
      return value;
    }
  }

  return undefined;
};

const getCorrelationId = (
  headers: Record<string, string | undefined>,
  metadata: AxiosMetadata | undefined
): string | undefined =>
  getHeaderValue(headers, ['x-correlation-id', 'X-Request-ID', 'x-request-id']) ??
  metadata?.correlationId;

const getRequestAttempts = (
  headers: Record<string, string | undefined>,
  metadata: AxiosMetadata | undefined
): number | undefined => {
  if (typeof metadata?.attemptCount === 'number') {
    return metadata.attemptCount;
  }

  const headerAttempt = Number(headers['x-attempt']);
  return Number.isNaN(headerAttempt) ? undefined : headerAttempt;
};

const getRequestDuration = (
  headers: Record<string, string | undefined>,
  metadata: AxiosMetadata | undefined
): number | undefined => {
  if (typeof metadata?.startTime === 'number') {
    return Date.now() - metadata.startTime;
  }

  const headerDuration = Number(headers['x-request-duration']);
  return Number.isNaN(headerDuration) ? undefined : headerDuration;
};

const buildNetworkApiError = (error: unknown): ApiError => {
  const axiosError = error as { message?: string; code?: unknown };
  const rawCode = asNonEmptyString(axiosError.code);
  const message = typeof axiosError.message === 'string' ? axiosError.message : '';
  const isTimeout = rawCode === 'ECONNABORTED' || /timeout/i.test(message);

  return new ApiError({
    message: isTimeout ? 'Request timed out' : 'Unable to connect to server',
    kind: isTimeout ? 'timeout' : 'network',
    code: rawCode ?? (isTimeout ? 'ECONNABORTED' : 'NETWORK_ERROR'),
    retryable: true,
    details: { message },
  });
};

export const normalizeApiError = (error: unknown): ApiError => {
  if (error instanceof ApiError) return error;

  if (isAxiosError(error)) {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as BackendErrorEnvelope | undefined;
      const headers = (error.response.headers ?? {}) as Record<string, string | undefined>;
      const metadata = getAxiosMetadata(error.config as AxiosRequestConfig | undefined);
      const code = getApiErrorCode(data, status);
      const message = getApiErrorMessage(data, error.message ?? '');
      const fields = getApiErrorFields(data);
      const kind = getApiErrorKind(status);
      const finalRetryable = getRetryable(status, data);
      const headerCorrelationId = getCorrelationId(headers, metadata);
      const requestAttempts = getRequestAttempts(headers, metadata);
      const requestDuration = getRequestDuration(headers, metadata);

      return new ApiError({
        message,
        kind,
        code,
        status,
        retryable: finalRetryable,
        correlationId: headerCorrelationId,
        attempts: requestAttempts,
        requestDurationMs: requestDuration,
        ...(fields ? { fields } : {}),
        ...(data ? { details: data } : {}),
      });
    }

    if (error.request) {
      return buildNetworkApiError(error);
    }
  }

  const message = error instanceof Error ? error.message : 'Unknown error';
  return new ApiError({
    message,
    kind: 'unknown',
    code: 'UNKNOWN_ERROR',
    retryable: false,
    details: error,
  });
};
