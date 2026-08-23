import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

import { DEFAULT_CORS_ORIGINS } from "../../domain/cors_contract.js";
import { ConfigurationError } from "./configuration_error.js";
import { parseEnvFile } from "./env_file.js";
import { type LlmServerConfig, loadLlmServerConfig } from "./provider_config.js";

export type { DashscopeTransportMode, LlmProvider, LlmServerConfig } from "./provider_config.js";
export { ConfigurationError };

/** The single converged prefix family; nothing outside it is read. */
const ENV_FILE_NAME = ".env.local";

const DEFAULT_DATABASE_URL = "sqlite:///./data/novel-engine.sqlite3";
const DEFAULT_HOST = "0.0.0.0";
const DEFAULT_PORT = 8000;
const DEFAULT_RATE_LIMIT = "5/minute";
const RATE_LIMIT_PATTERN = /^([1-9]\d{0,5})\/minute$/;

// Assembled like the Python sentinel so no credential-shaped literal ships in source.
export const DEFAULT_SECRET_KEY = ["change-me", "in-production", "32-char-long"].join("-");

/** Minimum usable secret length, mirroring the Python field constraint. */
const MIN_SECRET_LENGTH = 16;

const ENVIRONMENTS = ["development", "testing", "staging", "production"] as const;

export type ServerEnvironment = (typeof ENVIRONMENTS)[number];

export interface ServerConfig {
  readonly environment: ServerEnvironment;
  /**
   * Undefined when unset or the default outside production: the composition
   * root rotates a fresh random secret per start, invalidating all sessions.
   */
  readonly sessionSecret: string | undefined;
  readonly databaseUrl: string;
  readonly databasePath: string;
  readonly dataDirectory: string;
  readonly host: string;
  readonly port: number;
  readonly corsOrigins: string[];
  readonly trustedProxies: string[];
  readonly authRateLimitPerMinute: number;
  readonly llm: LlmServerConfig;
}

export interface LoadServerConfigInput {
  /** Process-style variables; defaults to `process.env`. File values never win. */
  readonly env?: Record<string, string | undefined>;
  /** `.env.local` location; defaults to `./.env.local`. `null` disables file loading. */
  readonly envFile?: string | null;
  /** Base for relative SQLite paths; defaults to `process.cwd()`. */
  readonly workingDirectory?: string;
}

/**
 * Resolve the operational configuration from `.env.local` plus the process
 * environment, apply the adjudicated defaults, and enforce the startup
 * guards — production misconfiguration fails here, before anything listens.
 */
export function loadServerConfig(input: LoadServerConfigInput = {}): ServerConfig {
  const env = mergedEnvironment(input);
  const environment = environmentFrom(env);
  const databaseUrl = stringFrom(env, "DB_URL") ?? DEFAULT_DATABASE_URL;
  if (!databaseUrl.startsWith("sqlite:///")) {
    throw new ConfigurationError("DB_URL must use the self-hosted SQLite store (sqlite:///…)");
  }
  const workingDirectory = input.workingDirectory ?? process.cwd();
  const databasePath = resolve(workingDirectory, databaseUrl.slice("sqlite:///".length));
  const sessionSecret = secretFrom(stringFrom(env, "SECURITY_SECRET_KEY"));

  const config: ServerConfig = {
    environment,
    sessionSecret,
    databaseUrl,
    databasePath,
    dataDirectory: dirname(databasePath),
    host: stringFrom(env, "API_HOST") ?? DEFAULT_HOST,
    port: portFrom(env),
    corsOrigins: listFrom(env, "SECURITY_CORS_ORIGINS") ?? DEFAULT_CORS_ORIGINS,
    trustedProxies: listFrom(env, "SECURITY_TRUSTED_PROXIES") ?? [],
    authRateLimitPerMinute: rateLimitFrom(env),
    llm: loadLlmServerConfig(env),
  };
  assertStartupGuards(config);
  return config;
}

/** Re-assert the startup guards at the composition root (fail-fast seam). */
export function assertStartupGuards(config: ServerConfig): void {
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
 * Normalize the session secret like the Python gold standard: unset, empty,
 * or the default value rotate (or refuse, per the production guards), while
 * an explicitly short-but-real value fails validation everywhere.
 */
function secretFrom(rawSecret: string | undefined): string | undefined {
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

function mergedEnvironment(input: LoadServerConfigInput): Map<string, string> {
  const merged = new Map<string, string>();
  const envFile = input.envFile === undefined ? ENV_FILE_NAME : input.envFile;
  if (envFile !== null) {
    try {
      for (const [key, value] of Object.entries(parseEnvFile(readFileSync(envFile, "utf8")))) {
        merged.set(key.toLowerCase(), value);
      }
    } catch {
      // A missing or unreadable env file is the no-configuration case.
    }
  }
  const overrides = input.env ?? process.env;
  for (const [key, value] of Object.entries(overrides)) {
    if (value !== undefined) {
      merged.set(key.toLowerCase(), value);
    }
  }
  return merged;
}

/** Case-insensitive lookup, mirroring the Python settings' behavior. */
function stringFrom(env: Map<string, string>, key: string): string | undefined {
  return env.get(key.toLowerCase());
}

function listFrom(env: Map<string, string>, key: string): string[] | undefined {
  const raw = stringFrom(env, key);
  if (raw === undefined) {
    return undefined;
  }
  const entries = raw
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter((entry) => entry !== "");
  return entries.length === 0 ? undefined : entries;
}

function environmentFrom(env: Map<string, string>): ServerEnvironment {
  const raw = stringFrom(env, "APP_ENVIRONMENT") ?? "development";
  const normalized = raw.trim().toLowerCase();
  if (!ENVIRONMENTS.includes(normalized as ServerEnvironment)) {
    throw new ConfigurationError(
      `APP_ENVIRONMENT must be one of ${ENVIRONMENTS.join(", ")} (got "${raw}")`,
    );
  }
  return normalized as ServerEnvironment;
}

function portFrom(env: Map<string, string>): number {
  const raw = stringFrom(env, "API_PORT");
  if (raw === undefined) {
    return DEFAULT_PORT;
  }
  const port = Number(raw);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    throw new ConfigurationError(
      `API_PORT must be an integer between 1024 and 65535 (got "${raw}")`,
    );
  }
  return port;
}

function rateLimitFrom(env: Map<string, string>): number {
  const raw = stringFrom(env, "SECURITY_RATE_LIMIT") ?? DEFAULT_RATE_LIMIT;
  const match = raw.match(RATE_LIMIT_PATTERN);
  if (match === null) {
    throw new ConfigurationError(
      `SECURITY_RATE_LIMIT must look like "5/minute" — requests per minute (got "${raw}")`,
    );
  }
  return Number(match[1]);
}
