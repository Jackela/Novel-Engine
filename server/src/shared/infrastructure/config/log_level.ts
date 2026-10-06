import { ConfigurationError } from "./configuration_error.js";

/**
 * The structured logger's level surface (DR-041), split out of
 * `server_config.ts` so the config module stays inside the file-size budget.
 * `LOG_LEVEL` is the container/operator knob for log verbosity; an unknown
 * value fails startup instead of silently falling back, so a typo never hides
 * the fact that the requested level is not applied.
 */
const LOG_LEVELS = ["fatal", "error", "warn", "info", "debug", "trace", "silent"] as const;

export type LogLevel = (typeof LOG_LEVELS)[number];

export const DEFAULT_LOG_LEVEL: LogLevel = "info";

/** Resolve the configured level; case-insensitive, empty means the default. */
export function logLevelFrom(rawValue: string | undefined): LogLevel {
  if (rawValue === undefined) {
    return DEFAULT_LOG_LEVEL;
  }
  const normalized = rawValue.trim().toLowerCase();
  if (!(LOG_LEVELS as readonly string[]).includes(normalized)) {
    throw new ConfigurationError(
      `LOG_LEVEL must be one of ${LOG_LEVELS.join(", ")} (got "${rawValue}")`,
    );
  }
  return normalized as LogLevel;
}
