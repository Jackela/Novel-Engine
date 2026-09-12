/**
 * The browser-facing CORS contract, registered once by the API composition
 * root. Allowed request headers are exactly what routes use to authenticate
 * and correlate requests. Exposed response headers are the non-simple ones
 * browser code must be able to read: `x-request-id` is stamped on every
 * response for correlation, and `retry-after` rides on rate-limited and
 * capacity-exceeded error responses.
 */
export const CORS_ALLOWED_HEADERS = [
  "content-type",
  "authorization",
  "x-api-key",
  "x-request-id",
  "accept",
  "origin",
  "x-requested-with",
  "x-csrf-token",
  "idempotency-key",
];

export const CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"];

export const CORS_EXPOSED_HEADERS = ["x-request-id", "x-total-count", "retry-after"];
