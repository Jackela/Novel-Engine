import { describe, expect, it } from 'vitest';
import { AxiosError } from 'axios';
import { getRetryDelayMs, shouldAutoRetryRequest } from '@/lib/api/apiClient';

describe('apiClient retry helpers', () => {
  it('caps exponential backoff delay at configured max', () => {
    expect(getRetryDelayMs(1)).toBe(200);
    expect(getRetryDelayMs(2)).toBe(400);
    expect(getRetryDelayMs(3)).toBe(800);
    expect(getRetryDelayMs(6)).toBe(2000); // capped
  });

  it('retries idempotent requests on transient failures', () => {
    const config = {
      method: 'GET',
      metadata: { attemptCount: 1, maxAttempts: 3 },
    } as const;

    const error = new AxiosError('Network Error', undefined, config as any);
    (error as any).request = {};

    expect(shouldAutoRetryRequest(config as any, error)).toBe(true);
  });

  it('does not retry when max attempts are reached', () => {
    const config = {
      method: 'GET',
      metadata: { attemptCount: 3, maxAttempts: 3 },
    };

    const error = new AxiosError('Server Error', undefined, config as any, undefined, {
      status: 500,
      headers: {},
    } as any);

    expect(shouldAutoRetryRequest(config, error)).toBe(false);
  });

  it('does not retry mutating requests without idempotency header', () => {
    const config = {
      method: 'POST',
      metadata: { attemptCount: 1, maxAttempts: 3 },
    };

    const error = new AxiosError('Server Error', undefined, config as any, undefined, {
      status: 503,
      headers: {},
    } as any);

    expect(shouldAutoRetryRequest(config, error)).toBe(false);
  });

  it('retries mutation when idempotency header is present', () => {
    const config = {
      method: 'POST',
      metadata: { attemptCount: 1, maxAttempts: 3 },
      headers: {
        'Idempotency-Key': 'abc123',
      },
    };

    const error = new AxiosError('Server Error', undefined, config as any, undefined, {
      status: 503,
      headers: {},
    } as any);

    expect(shouldAutoRetryRequest(config as any, error)).toBe(true);
  });
});
