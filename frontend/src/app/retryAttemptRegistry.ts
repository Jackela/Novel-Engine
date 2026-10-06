import { parseSession } from "./apiContract";
import { isRecord } from "./typeGuards";
import type { Session } from "./types/studio";

/**
 * The durable client-side attempt keys of the two job-repeating studio
 * operations — job retry and proposal generation (DR-027). One key names one
 * logical operation: the user's click keeps it across the operation's internal
 * retries and across workbench navigation, an unknown-outcome reconcile
 * re-issues the same key, and a new user intent (or a definitively failed
 * one) gets a new key. Attempts live in sessionStorage and reset with the
 * authenticated session, so a logged-in browser never carries keys across
 * principals.
 */

const STORAGE_KEY = "novel_engine.retry_attempts.v1";

interface RetryAttemptRegistryState {
  readonly version: 1;
  readonly sessionId: string;
  readonly ownerId: string;
  readonly attempts: Record<string, string>;
}

function attemptScope(projectId: string, sourceJobId: string): string {
  return JSON.stringify([projectId, sourceJobId]);
}

function generateAttemptScope(projectId: string, documentId: string, operation: string): string {
  // The kind marker keeps generation scopes disjoint from retry scopes.
  return JSON.stringify(["generate", projectId, documentId, operation]);
}

function readRegistry(): RetryAttemptRegistryState | null {
  const encoded = sessionStorage.getItem(STORAGE_KEY);
  if (encoded === null) return null;
  try {
    const value: unknown = JSON.parse(encoded);
    if (
      !isRecord(value) ||
      value.version !== 1 ||
      typeof value.sessionId !== "string" ||
      typeof value.ownerId !== "string" ||
      !isRecord(value.attempts)
    ) {
      return null;
    }
    const attempts: Record<string, string> = {};
    for (const [scope, key] of Object.entries(value.attempts)) {
      if (typeof key !== "string") return null;
      attempts[scope] = key;
    }
    return {
      version: 1,
      sessionId: value.sessionId,
      ownerId: value.ownerId,
      attempts,
    };
  } catch {
    return null;
  }
}

function writeRegistry(state: RetryAttemptRegistryState): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function recordRetryAttemptSession(session: Session): void {
  if (session.owner_id === null) {
    clearRetryAttemptSession();
    return;
  }
  const current = readRegistry();
  if (current?.sessionId === session.session_id && current.ownerId === session.owner_id) return;
  writeRegistry({
    version: 1,
    sessionId: session.session_id,
    ownerId: session.owner_id,
    attempts: {},
  });
}

export function parseAndRecordRetrySession(value: unknown): Session {
  const session = parseSession(value);
  recordRetryAttemptSession(session);
  return session;
}

export function clearRetryAttemptSession(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function getOrCreateRetryAttemptKey(projectId: string, sourceJobId: string): string {
  const current = readRegistry();
  if (current === null) throw new Error("Retry session identity is unavailable.");
  const scope = attemptScope(projectId, sourceJobId);
  const existing = current.attempts[scope];
  if (existing !== undefined) return existing;
  const key = crypto.randomUUID();
  writeRegistry({ ...current, attempts: { ...current.attempts, [scope]: key } });
  return key;
}

export function clearRetryAttempt(projectId: string, sourceJobId: string, key: string): void {
  clearAttempt(attemptScope(projectId, sourceJobId), key);
}

/**
 * The attempt key of one logical proposal generation, or null while no session
 * identity is recorded: the request then travels without the header (the
 * server treats it as optional) instead of failing the click. The same key is
 * kept across the operation's re-issues, so a network-flap resend replays the
 * durable job instead of drafting a second one.
 */
export function getOrCreateGenerateAttemptKey(
  projectId: string,
  documentId: string,
  operation: string,
): string | null {
  const current = readRegistry();
  if (current === null) return null;
  const scope = generateAttemptScope(projectId, documentId, operation);
  const existing = current.attempts[scope];
  if (existing !== undefined) return existing;
  const key = crypto.randomUUID();
  writeRegistry({ ...current, attempts: { ...current.attempts, [scope]: key } });
  return key;
}

export function clearGenerateAttempt(
  projectId: string,
  documentId: string,
  operation: string,
  key: string,
): void {
  clearAttempt(generateAttemptScope(projectId, documentId, operation), key);
}

function clearAttempt(scope: string, key: string): void {
  const current = readRegistry();
  if (current === null) return;
  if (current.attempts[scope] !== key) return;
  const attempts = { ...current.attempts };
  delete attempts[scope];
  writeRegistry({ ...current, attempts });
}
