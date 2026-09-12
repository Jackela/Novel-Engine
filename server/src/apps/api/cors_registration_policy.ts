/**
 * The browser-facing CORS contract, registered once by the API composition
 * root. Allowed request headers cover what routes actually read
 * (`x-csrf-token`, `idempotency-key`, `x-request-id`, `content-type`) plus
 * entries kept for browser/client compatibility. Exposed response headers
 * are the non-simple ones
 * browser code must be able to read: `x-request-id` is stamped on every
 * response for correlation, and `retry-after` rides on rate-limited and
 * capacity-exceeded error responses.
 */
import cors from "@fastify/cors";
import type { FastifyInstance } from "fastify";
import { DEFAULT_CORS_ORIGINS } from "../../shared/domain/cors_contract.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import { corsAllowList } from "../../shared/interface/http/cors_policy.js";

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

export interface CorsOriginsAppOptions {
  /** Browser origins allowed by the setup same-origin check (default: dev set). */
  corsOrigins?: string[] | undefined;
  /** Resolved operational configuration from loadServerConfig. */
  readonly config?: ServerConfig | undefined;
}

/** Effective browser origin allow-list: explicit option, config, then the dev set. */
export function resolveCorsOrigins(options: CorsOriginsAppOptions): string[] {
  return options.corsOrigins ?? options.config?.corsOrigins ?? DEFAULT_CORS_ORIGINS;
}

/** Register the shared CORS contract for every route of the app. */
export async function registerCors(app: FastifyInstance, corsOrigins: string[]): Promise<void> {
  const allowList = corsAllowList(corsOrigins);
  await app.register(cors, {
    origin: allowList.allowAll ? true : allowList.origins,
    credentials: true,
    allowedHeaders: CORS_ALLOWED_HEADERS,
    methods: CORS_ALLOWED_METHODS,
    exposedHeaders: CORS_EXPOSED_HEADERS,
    maxAge: 600,
  });
}
