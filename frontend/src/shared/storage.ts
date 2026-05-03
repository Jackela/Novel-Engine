import type { SessionCatalog, SessionState } from '@/app/types';

export const sessionStorageKey = 'novel-engine-session';
export const sessionCatalogStorageKey = 'novel-engine-session-catalog';
const SESSION_CATALOG_VERSION = 2;

export const safeStorage = {
  read<T>(key: string): T | null {
    if (typeof window === 'undefined') {
      return null;
    }

    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  },

  write<T>(key: string, value: T) {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(key, JSON.stringify(value));
  },

  remove(key: string) {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.removeItem(key);
  },
};

function nowIso() {
  return new Date().toISOString();
}

function sortSessionsByRecency(sessions: SessionState[]): SessionState[] {
  return [...sessions].sort((left, right) =>
    (right.updatedAt ?? '').localeCompare(left.updatedAt ?? ''),
  );
}

export function buildSessionId(session: Pick<SessionState, 'kind' | 'workspaceId'>): string {
  return `${session.kind}:${session.workspaceId}`;
}

export function normalizeSession(session: SessionState): SessionState {
  const timestamp = nowIso();
  return {
    ...session,
    id: session.id || buildSessionId(session),
    createdAt: session.createdAt ?? timestamp,
    updatedAt: session.updatedAt ?? timestamp,
    lastStoryId: session.lastStoryId ?? null,
    lastRunId: session.lastRunId ?? null,
    lastView: session.lastView ?? 'workspace',
  };
}

function writeLegacySession(activeSession: SessionState | null) {
  if (!activeSession) {
    safeStorage.remove(sessionStorageKey);
    return;
  }

  safeStorage.write(sessionStorageKey, {
    kind: activeSession.kind,
    workspaceId: activeSession.workspaceId,
    token: activeSession.token,
    refreshToken: activeSession.refreshToken,
    user: activeSession.user,
  });
}

export function emptySessionCatalog(): SessionCatalog {
  return {
    version: SESSION_CATALOG_VERSION,
    activeSessionId: null,
    sessions: [],
  };
}

export function getActiveSession(catalog: SessionCatalog): SessionState | null {
  return (
    catalog.sessions.find((session) => session.id === catalog.activeSessionId) ?? null
  );
}

export function findLatestSession(
  catalog: SessionCatalog,
  kind?: SessionState['kind'],
): SessionState | null {
  const sessions = kind
    ? catalog.sessions.filter((session) => session.kind === kind)
    : catalog.sessions;
  return sortSessionsByRecency(sessions)[0] ?? null;
}

export function writeSessionCatalog(catalog: SessionCatalog) {
  const normalizedSessions = sortSessionsByRecency(
    catalog.sessions.map((session) => normalizeSession(session)),
  );
  const nextCatalog: SessionCatalog = {
    version: SESSION_CATALOG_VERSION,
    activeSessionId: catalog.activeSessionId,
    sessions: normalizedSessions,
  };

  safeStorage.write(sessionCatalogStorageKey, nextCatalog);
  writeLegacySession(getActiveSession(nextCatalog));
}

export function upsertSession(
  catalog: SessionCatalog,
  session: SessionState,
  options?: { makeActive?: boolean },
): SessionCatalog {
  const normalized = normalizeSession({
    ...session,
    updatedAt: nowIso(),
  });
  const sessions = catalog.sessions.filter(
    (existing) => existing.id !== normalized.id,
  );
  const nextCatalog: SessionCatalog = {
    version: SESSION_CATALOG_VERSION,
    activeSessionId: options?.makeActive === false ? catalog.activeSessionId : normalized.id,
    sessions: sortSessionsByRecency([normalized, ...sessions]),
  };
  writeSessionCatalog(nextCatalog);
  return nextCatalog;
}

export function setActiveSessionId(
  catalog: SessionCatalog,
  activeSessionId: string | null,
): SessionCatalog {
  const nextCatalog: SessionCatalog = {
    version: SESSION_CATALOG_VERSION,
    activeSessionId,
    sessions: sortSessionsByRecency(catalog.sessions.map((session) => normalizeSession(session))),
  };
  writeSessionCatalog(nextCatalog);
  return nextCatalog;
}

export function removeSession(
  catalog: SessionCatalog,
  sessionId: string,
): SessionCatalog {
  const sessions = catalog.sessions.filter((session) => session.id !== sessionId);
  const nextCatalog: SessionCatalog = {
    version: SESSION_CATALOG_VERSION,
    activeSessionId:
      catalog.activeSessionId === sessionId ? null : catalog.activeSessionId,
    sessions: sortSessionsByRecency(sessions),
  };
  writeSessionCatalog(nextCatalog);
  return nextCatalog;
}

export function updateSessionSelection(
  catalog: SessionCatalog,
  sessionId: string,
  patch: Pick<SessionState, 'lastStoryId' | 'lastRunId' | 'lastView'>,
): SessionCatalog {
  const sessions = catalog.sessions.map((session) =>
    session.id === sessionId
      ? normalizeSession({
          ...session,
          ...patch,
          updatedAt: nowIso(),
        })
      : normalizeSession(session),
  );
  const nextCatalog: SessionCatalog = {
    version: SESSION_CATALOG_VERSION,
    activeSessionId: catalog.activeSessionId,
    sessions: sortSessionsByRecency(sessions),
  };
  writeSessionCatalog(nextCatalog);
  return nextCatalog;
}

export function readSessionCatalog(): SessionCatalog {
  const stored = safeStorage.read<SessionCatalog>(sessionCatalogStorageKey);
  if (stored?.version === SESSION_CATALOG_VERSION && Array.isArray(stored.sessions)) {
    return {
      version: SESSION_CATALOG_VERSION,
      activeSessionId: stored.activeSessionId ?? null,
      sessions: sortSessionsByRecency(
        stored.sessions.map((session) => normalizeSession(session)),
      ),
    };
  }

  const legacySession = safeStorage.read<{
    kind?: SessionState['kind'];
    workspaceId?: string;
    token?: string;
    refreshToken?: string;
    user?: SessionState['user'];
  }>(sessionStorageKey);
  if (!legacySession?.kind || !legacySession.workspaceId) {
    return emptySessionCatalog();
  }

  const migratedSession = normalizeSession({
    id: buildSessionId({
      kind: legacySession.kind,
      workspaceId: legacySession.workspaceId,
    }),
    kind: legacySession.kind,
    workspaceId: legacySession.workspaceId,
    token: legacySession.token,
    refreshToken: legacySession.refreshToken,
    user: legacySession.user,
  });
  const nextCatalog: SessionCatalog = {
    version: SESSION_CATALOG_VERSION,
    activeSessionId: migratedSession.id,
    sessions: [migratedSession],
  };
  writeSessionCatalog(nextCatalog);
  return nextCatalog;
}
