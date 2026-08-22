export interface RateLimitDecision {
  allowed: boolean;
  /** Whole seconds until the key may retry; at least 1 when not allowed. */
  retryAfterSeconds: number;
}

/**
 * Rate limiting port: the interface layer asks per request whether the key
 * (client identity + endpoint) is within the limit; the token-bucket
 * implementation in infrastructure decides.
 */
export interface RateLimiter {
  check(key: string): RateLimitDecision;
}
