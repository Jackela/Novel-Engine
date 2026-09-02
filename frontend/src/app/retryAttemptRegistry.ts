import { parseSession } from "./apiContract";
import type { Session } from "./types/studio";

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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
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
  const current = readRegistry();
  if (current === null) return;
  const scope = attemptScope(projectId, sourceJobId);
  if (current.attempts[scope] !== key) return;
  const attempts = { ...current.attempts };
  delete attempts[scope];
  writeRegistry({ ...current, attempts });
}
