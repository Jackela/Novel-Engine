import type { FastifyInstance } from "fastify";

import type { AuthService } from "../../shared/application/auth_service.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import { clientIdentity } from "../../shared/infrastructure/rate_limit/client_identity.js";
import { TokenBucketRateLimiter } from "../../shared/infrastructure/rate_limit/token_bucket.js";
import type { ProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";
import { authRoutes } from "../../shared/interface/http/auth_routes.js";

const DEFAULT_AUTH_RATE_LIMIT_PER_MINUTE = 5;
/** Rate-limit buckets expire with the minute window that fills them. */
const AUTH_RATE_LIMIT_KEY_TTL_SECONDS = 60;

export interface AuthRegistrationInputs {
  /** Absent while the app is database-free; auth surfaces then answer 503. */
  authService: AuthService | undefined;
  productIdentity: ProductIdentity;
  environment: string;
  corsOrigins: string[];
}

export interface AuthRegistrationOptions {
  /** Auth endpoint rate limit in requests per minute (default: five). */
  authRateLimitPerMinute?: number | undefined;
  /** Trusted proxy IPs/CIDRs/hosts for rate-limit client identity (default: none). */
  trustedProxies?: string[] | undefined;
  /** Resolved operational configuration from loadServerConfig. */
  readonly config?: ServerConfig | undefined;
}

/** Register the auth routes with their per-minute token-bucket rate limit. */
export async function registerAuthRoutes(
  app: FastifyInstance,
  inputs: AuthRegistrationInputs,
  options: AuthRegistrationOptions,
): Promise<void> {
  const perMinute =
    options.authRateLimitPerMinute ??
    options.config?.authRateLimitPerMinute ??
    DEFAULT_AUTH_RATE_LIMIT_PER_MINUTE;
  await app.register(authRoutes, {
    authService: inputs.authService,
    limiter: new TokenBucketRateLimiter({
      ratePerSecond: perMinute / 60,
      capacity: perMinute,
      keyTtlSeconds: AUTH_RATE_LIMIT_KEY_TTL_SECONDS,
    }),
    productIdentity: inputs.productIdentity,
    environment: inputs.environment,
    corsOrigins: inputs.corsOrigins,
    resolveClientIdentity: (request) =>
      clientIdentity(
        request.socket?.remoteAddress,
        typeof request.headers["x-forwarded-for"] === "string"
          ? request.headers["x-forwarded-for"]
          : undefined,
        options.trustedProxies ?? options.config?.trustedProxies ?? [],
      ),
  });
}
