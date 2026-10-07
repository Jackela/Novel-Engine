import { readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

import { DEFAULT_CORS_ORIGINS } from "../../domain/cors_contract.js";
import { errorCode } from "../error_code.js";
import { locateWorkspaceRoot } from "../workspace_manifest.js";
import { ConfigurationError } from "./configuration_error.js";
import { parseEnvFile } from "./env_file.js";
import { integerFrom, listFrom, stringFrom } from "./env_values.js";
import { type LogLevel, logLevelFrom } from "./log_level.js";
import { type LlmServerConfig, loadLlmServerConfig } from "./provider_config.js";
import { assertStartupGuards, secretFrom } from "./startup_guards.js";
import {
  assertWorkflowCapacity,
  DEFAULT_MAX_ACTIVE_WORKFLOWS,
  DEFAULT_MAX_ACTIVE_WORKFLOWS_PER_PROJECT,
  MAX_ACTIVE_WORKFLOWS,
  MIN_ACTIVE_WORKFLOWS,
} from "./workflow_capacity.js";

/** Same seam for the guards: `loadServerConfig` and `buildApp` share one import point. */
export { assertStartupGuards, DEFAULT_SECRET_KEY } from "./startup_guards.js";
/** Re-exported so the composition-root seam keeps one import location. */
export { assertWorkflowCapacity, type WorkflowCapacityConfig } from "./workflow_capacity.js";
export { ConfigurationError };

/** The single converged prefix family; nothing outside it is read. */
const ENV_FILE_NAME = ".env.local";

const DEFAULT_DATABASE_URL = "sqlite:///./data/novel-engine.sqlite3";
const DEFAULT_HOST = "0.0.0.0";
const DEFAULT_PORT = 8000;
const DEFAULT_RATE_LIMIT = "5/minute";
const RATE_LIMIT_PATTERN = /^([1-9]\d{0,5})\/minute$/;

const ENVIRONMENTS = ["development", "testing", "staging", "production"] as const;

type ServerEnvironment = (typeof ENVIRONMENTS)[number];

/**
 * The pino levels the server logger accepts (DR-041) live in `log_level.ts`;
 * re-exported here so the config surface keeps one import location.
 */
export { type LogLevel, logLevelFrom } from "./log_level.js";

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
  /** Pino level of the structured server logger; `info` when unset. */
  readonly logLevel: LogLevel;
  readonly corsOrigins: string[];
  /**
   * Concrete proxy addresses only. Network ranges are refused: a range that
   * covers clients would let a client pose as a trusted proxy and rotate
   * forged forwarding chains into fresh rate-limit buckets.
   */
  readonly trustedProxies: string[];
  readonly authRateLimitPerMinute: number;
  readonly maxActiveWorkflows: number;
  readonly maxActiveWorkflowsPerProject: number;
  readonly llm: LlmServerConfig;
}

export interface LoadServerConfigInput {
  /** Process-style variables; defaults to `process.env`. File values never win. */
  readonly env?: Record<string, string | undefined>;
  /**
   * `.env.local` location; defaults to the workspace root's `.env.local`
   * (independent of the current working directory). `null` disables file loading.
   */
  readonly envFile?: string | null;
  /** Base for relative SQLite paths; defaults to the workspace root. */
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
  const workingDirectory = input.workingDirectory ?? locateWorkspaceRoot();
  const databasePath = resolve(workingDirectory, databaseUrl.slice("sqlite:///".length));
  const sessionSecret = secretFrom(stringFrom(env, "SECURITY_SECRET_KEY"));
  const maxActiveWorkflows = integerFrom(
    env,
    "API_MAX_ACTIVE_WORKFLOWS",
    DEFAULT_MAX_ACTIVE_WORKFLOWS,
    MIN_ACTIVE_WORKFLOWS,
    MAX_ACTIVE_WORKFLOWS,
  );
  const maxActiveWorkflowsPerProject = integerFrom(
    env,
    "API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT",
    DEFAULT_MAX_ACTIVE_WORKFLOWS_PER_PROJECT,
    MIN_ACTIVE_WORKFLOWS,
    MAX_ACTIVE_WORKFLOWS,
  );
  assertWorkflowCapacity({
    applicationLimit: maxActiveWorkflows,
    projectLimit: maxActiveWorkflowsPerProject,
  });

  const config: ServerConfig = {
    environment,
    sessionSecret,
    databaseUrl,
    databasePath,
    dataDirectory: dirname(databasePath),
    host: stringFrom(env, "API_HOST") ?? DEFAULT_HOST,
    port: portFrom(env),
    logLevel: logLevelFromEnv(env),
    corsOrigins: listFrom(env, "SECURITY_CORS_ORIGINS") ?? DEFAULT_CORS_ORIGINS,
    trustedProxies: listFrom(env, "SECURITY_TRUSTED_PROXIES") ?? [],
    authRateLimitPerMinute: rateLimitFrom(env),
    maxActiveWorkflows,
    maxActiveWorkflowsPerProject,
    llm: loadLlmServerConfig(env),
  };
  assertStartupGuards(config);
  return config;
}

function mergedEnvironment(input: LoadServerConfigInput): Map<string, string> {
  const merged = new Map<string, string>();
  // The workspace root resolves lazily so fully-explicit inputs never touch the locator.
  const envFile =
    input.envFile === undefined ? join(locateWorkspaceRoot(), ENV_FILE_NAME) : input.envFile;
  if (envFile !== null) {
    const contents = readOptionalEnvironmentFile(envFile);
    if (contents !== undefined) {
      for (const [key, value] of Object.entries(parseEnvFile(contents))) {
        merged.set(key.toLowerCase(), value);
      }
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

function readOptionalEnvironmentFile(filePath: string): string | undefined {
  try {
    if (!statSync(filePath).isFile()) {
      throw new ConfigurationError(`Environment file must be a regular file: ${filePath}`);
    }
    return readFileSync(filePath, "utf8");
  } catch (error) {
    if (isMissingFileError(error)) {
      return undefined;
    }
    throw error;
  }
}

function isMissingFileError(error: unknown): boolean {
  return errorCode(error) === "ENOENT";
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

/**
 * The structured logger's level (DR-041). Case-insensitive; an unknown value
 * is a configuration error so a typo cannot silently keep the default.
 */
function logLevelFromEnv(env: Map<string, string>): LogLevel {
  return logLevelFrom(stringFrom(env, "LOG_LEVEL"));
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
