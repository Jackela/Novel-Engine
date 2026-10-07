import { ConfigurationError } from "./configuration_error.js";

/**
 * Env-value readers shared by the two config loaders. `server_config.ts` and
 * `provider_config.ts` read the same merged map (lowercased keys, string
 * values) with the same rules, so the lookup, list, and bounded-number
 * readers live here once instead of drifting apart in each file. Every reader
 * treats an absent or blank value as unset — Compose passes an unset
 * variable through as an empty string — so a blank never silently reads as
 * zero; a present value that fails its bounds fails startup with a
 * `ConfigurationError` naming the key and quoting the rejected value.
 */

/** Case-insensitive lookup: merged environment keys are stored lowercased. */
export function stringFrom(env: ReadonlyMap<string, string>, key: string): string | undefined {
  return env.get(key.toLowerCase());
}

/**
 * Comma-separated list value (CORS origins, trusted proxies): entries are
 * trimmed and lowercased, blank entries are dropped, and a value that yields
 * no entry at all — unset, empty, or only separators — is undefined so the
 * caller's defaults apply.
 */
export function listFrom(env: ReadonlyMap<string, string>, key: string): string[] | undefined {
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

/**
 * Integer within the inclusive `[minimum, maximum]` range; an absent or blank
 * value keeps the fallback. A non-integer or out-of-range value fails startup
 * instead of silently keeping the default, so a typo cannot pass unnoticed.
 */
export function integerFrom(
  env: ReadonlyMap<string, string>,
  key: string,
  fallback: number,
  minimum: number,
  maximum: number,
): number {
  const raw = stringFrom(env, key);
  if (raw === undefined || raw.trim() === "") return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new ConfigurationError(
      `${key} must be an integer between ${minimum} and ${maximum} (got "${raw}")`,
    );
  }
  return value;
}

/**
 * Finite number within the inclusive `[minimum, maximum]` range, fractional
 * values included (the seconds-form LLM retry delay); the absent/blank
 * fallback and the failure semantics match `integerFrom`, only the range test
 * differs so a decimal is accepted.
 */
export function numberFrom(
  env: ReadonlyMap<string, string>,
  key: string,
  fallback: number,
  minimum: number,
  maximum: number,
): number {
  const raw = stringFrom(env, key);
  if (raw === undefined || raw.trim() === "") return fallback;
  const value = Number(raw);
  if (!Number.isFinite(value) || value < minimum || value > maximum) {
    throw new ConfigurationError(
      `${key} must be a number between ${minimum} and ${maximum} (got "${raw}")`,
    );
  }
  return value;
}
