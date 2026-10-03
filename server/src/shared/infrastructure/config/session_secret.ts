import { randomBytes } from "node:crypto";
import { chmodSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { errorCode } from "../error_code.js";
import { ConfigurationError } from "./configuration_error.js";

/**
 * Persisted generated session secret (DR-040). Without this module a
 * non-container start without `SECURITY_SECRET_KEY` rotates a fresh random
 * key on every process start, so every restart silently logs every author
 * out. The generated key is written once into the data directory (0600,
 * next to the database and the setup token) and reused by later starts.
 */
export const SESSION_SECRET_FILE_NAME = ".secret";

/** The generated secret's entropy: 32 bytes rendered as 64 hex characters. */
const GENERATED_SECRET_BYTES = 32;

/** Only the file's owner may read or write the persisted key. */
const SECRET_FILE_MODE = 0o600;

/**
 * Environments where a missing secret is a configuration error, never a
 * silent rotation: `loadServerConfig` already refuses to start them without
 * `SECURITY_SECRET_KEY`, so the composition root must not invent one — that
 * keeps the DR-033 production guard the single authority.
 */
const GUARDED_ENVIRONMENTS: ReadonlySet<string> = new Set(["production", "staging"]);

export interface ResolveSessionSecretInput {
  /** The explicitly configured secret (`SECURITY_SECRET_KEY`); always wins. */
  readonly configured: string | undefined;
  /** The resolved environment name; guarded environments never persist one. */
  readonly environment: string;
  /**
   * The persistent data directory. Without one (a database-free app) there is
   * no durable location for the key, so the per-start fallback stays.
   */
  readonly dataDirectory: string | undefined;
}

/**
 * Resolve the session secret: an explicit configuration wins verbatim; a
 * guarded environment (production/staging) returns undefined so the caller
 * keeps the existing per-start rotation; every other deployment reads the
 * generated key from `<dataDirectory>/.secret`, creating it once (0600) when
 * absent. An unreadable, undecodable, or empty file fails startup loudly —
 * silently rotating would invalidate every session on the next restart,
 * which is exactly the failure this module exists to remove.
 */
export function resolveSessionSecret(input: ResolveSessionSecretInput): string | undefined {
  if (input.configured !== undefined) {
    return input.configured;
  }
  if (input.dataDirectory === undefined || GUARDED_ENVIRONMENTS.has(input.environment)) {
    return undefined;
  }
  const filePath = join(input.dataDirectory, SESSION_SECRET_FILE_NAME);
  const existing = readPersistedSecret(filePath);
  if (existing !== undefined) {
    return existing;
  }
  return createPersistedSecret(filePath);
}

/** Read and trim the persisted key; `undefined` means the file does not exist. */
function readPersistedSecret(filePath: string): string | undefined {
  let contents: string;
  try {
    contents = readFileSync(filePath, "utf8");
  } catch (error) {
    if (errorCode(error) === "ENOENT") {
      return undefined;
    }
    throw error;
  }
  const trimmed = contents.trim();
  if (trimmed === "") {
    throw new ConfigurationError(
      `Session secret file ${filePath} is empty; delete it to generate a new key ` +
        "or set SECURITY_SECRET_KEY explicitly",
    );
  }
  return trimmed;
}

/**
 * Create the key exactly once. `wx` fails on an existing file instead of
 * overwriting it, so two concurrently starting processes cannot disagree
 * about the key; the loser re-reads the winner's value. The explicit chmod
 * is defense in depth for filesystems that ignore the creation mode.
 */
function createPersistedSecret(filePath: string): string {
  const secret = randomBytes(GENERATED_SECRET_BYTES).toString("hex");
  try {
    writeFileSync(filePath, `${secret}\n`, { mode: SECRET_FILE_MODE, flag: "wx" });
    chmodSync(filePath, SECRET_FILE_MODE);
    return secret;
  } catch (error) {
    if (errorCode(error) === "EEXIST") {
      const concurrent = readPersistedSecret(filePath);
      if (concurrent !== undefined) {
        return concurrent;
      }
    }
    throw error;
  }
}
