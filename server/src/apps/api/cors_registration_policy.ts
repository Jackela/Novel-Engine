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
