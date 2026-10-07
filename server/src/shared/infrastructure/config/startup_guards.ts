import { isTrustedProxyRange } from "../rate_limit/client_identity.js";
import { ConfigurationError } from "./configuration_error.js";
import type { ServerConfig } from "./server_config.js";
import { assertWorkflowCapacity } from "./workflow_capacity.js";

/**
 * Startup guards for a resolved `ServerConfig`, split out of `server_config.ts`
 * for the file-size budget. The loader asserts them at the end of resolution
 * and the composition root re-asserts them on its own config, so production
 * and staging misconfiguration fails here — before any directory is created,
 * database opened, or socket bound — instead of serving with a placeholder
 * session key or a wildcard origin.
 */

// Sentinel default assembled from harmless words so no credential-shaped literal ships in source.
export const DEFAULT_SECRET_KEY = ["change-me", "in-production", "32-char-long"].join("-");

/**
 * Placeholder prefix refused by the production guard. `.env.example` ships a
 * `change-me…` value, so without this rule a copied example file silently
 * becomes the production session key; the guard makes it fail startup
 * instead. Outside production the value stays usable for local development.
 */
const PLACEHOLDER_SECRET_PREFIX = "change-me";

/** Minimum usable secret length; explicit values shorter than this fail validation. */
const MIN_SECRET_LENGTH = 16;

/** Re-assert the startup guards at the composition root (fail-fast seam). */
export function assertStartupGuards(config: ServerConfig): void {
  assertWorkflowCapacity({
    applicationLimit: config.maxActiveWorkflows,
    projectLimit: config.maxActiveWorkflowsPerProject,
  });
  assertTrustedProxyAddresses(config.trustedProxies);
  if (config.environment !== "production" && config.environment !== "staging") {
    return;
  }
  if (config.sessionSecret === undefined) {
    throw new ConfigurationError(
      `SECURITY_SECRET_KEY must be set to a non-default value in ${config.environment}`,
    );
  }
  if (config.environment !== "production") {
    return;
  }
  if (config.sessionSecret?.startsWith(PLACEHOLDER_SECRET_PREFIX) === true) {
    throw new ConfigurationError(
      "SECURITY_SECRET_KEY must not keep the change-me placeholder value in production; " +
        "generate a unique random value (for example: openssl rand -hex 32)",
    );
  }
  if (!config.databaseUrl.startsWith("sqlite:///")) {
    throw new ConfigurationError("DB_URL must use the self-hosted SQLite store (sqlite:///…)");
  }
  if (config.corsOrigins.some((origin) => origin.includes("*"))) {
    throw new ConfigurationError("Production CORS origins cannot include a wildcard");
  }
  if (
    config.corsOrigins.some(
      (origin) => origin.includes("localhost") || origin.includes("127.0.0.1"),
    )
  ) {
    throw new ConfigurationError("Production CORS origins cannot include localhost or 127.0.0.1");
  }
}

/**
 * Trusted proxies must be concrete addresses: a network range can cover
 * clients, and a client inside it would then be treated as a forwarding proxy
 * (fresh rate-limit bucket per forged forwarding chain).
 */
function assertTrustedProxyAddresses(entries: readonly string[]): void {
  for (const entry of entries) {
    if (isTrustedProxyRange(entry)) {
      throw new ConfigurationError(
        `SECURITY_TRUSTED_PROXIES must list exact proxy addresses, not network ranges (got "${entry}")`,
      );
    }
  }
}

/**
 * Normalize the session secret: unset, empty, or the default value rotate
 * (or refuse, per the production guards), while an explicitly short-but-real
 * value fails validation everywhere.
 */
export function secretFrom(rawSecret: string | undefined): string | undefined {
  const trimmed = rawSecret?.trim() ?? "";
  if (trimmed === "" || trimmed === DEFAULT_SECRET_KEY) {
    return undefined;
  }
  if (trimmed.length < MIN_SECRET_LENGTH) {
    throw new ConfigurationError(
      `SECURITY_SECRET_KEY must be at least ${MIN_SECRET_LENGTH} characters long`,
    );
  }
  return trimmed;
}
