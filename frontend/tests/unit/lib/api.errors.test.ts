import { describe, it, expect, vi } from 'vitest';
import { AxiosError, type AxiosRequestConfig } from 'axios';
import { ApiError, normalizeApiError } from '@/lib/api/errors';

const baseConfig: AxiosRequestConfig = { url: '/api/test' };

describe('normalizeApiError', () => {
  it('maps backend envelope with code, detail, and fields', () => {
    const response = {
      status: 400,
      statusText: 'Bad Request',
      headers: {},
      config: baseConfig,
      data: {
        code: 'BAD_INPUT',
        detail: 'Invalid payload',
        fields: [{ path: 'name', message: 'Name is required', type: 'value_error.missing' }],
      },
    };

    const axiosErr = new AxiosError('Request failed', 'ERR_BAD_REQUEST', baseConfig, {}, response);
    const normalized = normalizeApiError(axiosErr);

    expect(normalized).toBeInstanceOf(ApiError);
    expect(normalized.kind).toBe('http');
    expect(normalized.status).toBe(400);
    expect(normalized.code).toBe('BAD_INPUT');
    expect(normalized.fields?.[0]).toMatchObject({ path: 'name', message: 'Name is required' });
    expect(normalized.recoverable).toBe(false);
  });

  it('extracts FastAPI validation details into fields', () => {
    const response = {
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: {},
      config: baseConfig,
      data: {
        detail: [
          { loc: ['body', 'email'], msg: 'Invalid email', type: 'value_error.email' },
        ],
      },
    };

    const axiosErr = new AxiosError('Validation failed', 'ERR_BAD_REQUEST', baseConfig, {}, response);
    const normalized = normalizeApiError(axiosErr);

    expect(normalized.kind).toBe('validation');
    expect(normalized.status).toBe(422);
    expect(normalized.fields?.[0]).toMatchObject({ path: 'body.email', message: 'Invalid email' });
    expect(normalized.recoverable).toBe(false);
  });

  it('treats ECONNABORTED as timeout and marks retryable', () => {
    const axiosErr = new AxiosError('timeout', 'ECONNABORTED', baseConfig);
    (axiosErr as any).request = {};

    const normalized = normalizeApiError(axiosErr);
    expect(normalized.kind).toBe('timeout');
    expect(normalized.code).toBe('ECONNABORTED');
    expect(normalized.recoverable).toBe(true);
  });

  it('treats network failure without response as network error', () => {
    const axiosErr = new AxiosError('Network Error', 'ERR_NETWORK', baseConfig);
    (axiosErr as any).request = {};

    const normalized = normalizeApiError(axiosErr);
    expect(normalized.kind).toBe('network');
    expect(normalized.code).toBe('ERR_NETWORK');
    expect(normalized.recoverable).toBe(true);
    expect(normalized.message).toContain('Unable to connect');
  });

  it('captures correlation metadata and duration from tracked requests', () => {
    const mockedTime = 500;
    const metadataConfig: AxiosRequestConfig = {
      ...baseConfig,
      metadata: { correlationId: 'corr-id', attemptCount: 2, startTime: 250 },
    };

    const response = {
      status: 500,
      statusText: 'Server Error',
      headers: {},
      config: metadataConfig,
      data: {
        code: 'SERVER_ERROR',
      },
    };

    vi.spyOn(Date, 'now').mockReturnValue(mockedTime);
    try {
      const axiosErr = new AxiosError('Server error', 'ERR_SERVER', metadataConfig, {}, response);
      const normalized = normalizeApiError(axiosErr);

      expect(normalized.correlationId).toBe('corr-id');
      expect(normalized.attempts).toBe(2);
      expect(normalized.requestDurationMs).toBe(mockedTime - 250);
    } finally {
      vi.restoreAllMocks();
    }
  });

  it('falls back to header correlation id and attempt counts when metadata is absent', () => {
    const response = {
      status: 500,
      statusText: 'Server Error',
      headers: {
        'x-correlation-id': 'header-correlator',
        'x-attempt': '3',
        'x-request-duration': '159',
      },
      config: baseConfig,
      data: {
        code: 'SERVER_ERROR',
      },
    };

    const axiosErr = new AxiosError('Server error', 'ERR_SERVER', baseConfig, {}, response);
    const normalized = normalizeApiError(axiosErr);

    expect(normalized.correlationId).toBe('header-correlator');
    expect(normalized.attempts).toBe(3);
    expect(normalized.requestDurationMs).toBe(159);
  });
});
