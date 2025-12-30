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

export const normalizeApiError = (error: unknown): ApiError => {
  if (error instanceof ApiError) return error;

  if (isAxiosError(error)) {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as BackendErrorEnvelope | undefined;
      const headers = (error.response.headers ?? {}) as Record<string, string | undefined>;
      const requestConfig = error.config as AxiosRequestConfig | undefined;
      const metadata = requestConfig?.metadata as {
        startTime?: number;
        correlationId?: string;
        attemptCount?: number;
      } | undefined;

      const code =
        asNonEmptyString(data?.code) ??
        asNonEmptyString((data?.error as Record<string, unknown> | undefined)?.code) ??
        `HTTP_${status}`;

      const detailText = asNonEmptyString(data?.detail);
      const errorText = asNonEmptyString(data?.error);
      const messageText = asNonEmptyString((data as Record<string, unknown> | undefined)?.message);

      const message = detailText ?? messageText ?? errorText ?? error.message ?? 'Request failed';

      const fields =
        normalizeValidationFields(data?.fields) ??
        normalizeFastApiValidation((data as Record<string, unknown> | undefined)?.detail);

      const kind: ApiErrorKind =
        status === 401 || status === 403
          ? 'auth'
          : status === 422
            ? 'validation'
            : 'http';

      const retryable = status === 408 || status === 429 || status >= 500;
      const serverRetryable = typeof data?.retryable === 'boolean' ? data.retryable : undefined;
      const finalRetryable = serverRetryable ?? retryable;

      const headerCorrelationId =
        asNonEmptyString(headers['x-correlation-id']) ||
        asNonEmptyString(headers['X-Request-ID']) ||
        asNonEmptyString(headers['x-request-id']) ||
        metadata?.correlationId;
      const headerAttempt = Number(headers['x-attempt']);
      const requestAttempts =
        typeof metadata?.attemptCount === 'number'
          ? metadata.attemptCount
          : !Number.isNaN(headerAttempt)
            ? headerAttempt
            : undefined;
      const headerDuration = Number(headers['x-request-duration']);
      const requestDuration =
        typeof metadata?.startTime === 'number'
          ? Date.now() - metadata.startTime
          : !Number.isNaN(headerDuration)
            ? headerDuration
            : undefined;

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
      const rawCode = asNonEmptyString((error as unknown as { code?: unknown }).code);
      const isTimeout = rawCode === 'ECONNABORTED' || /timeout/i.test(error.message || '');

      return new ApiError({
        message: isTimeout ? 'Request timed out' : 'Unable to connect to server',
        kind: isTimeout ? 'timeout' : 'network',
        code: rawCode ?? (isTimeout ? 'ECONNABORTED' : 'NETWORK_ERROR'),
        retryable: true,
        details: { message: error.message },
      });
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
