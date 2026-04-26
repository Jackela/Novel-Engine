import {
  createContext,
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react';

import { api } from '@/app/api';
import type {
  ActiveWorkspaceSummary,
  CurrentUserResponse,
  GuestSessionResponse,
  LoginRequest,
  LoginResponse,
  SessionCatalog,
  SessionState,
  StorySurfaceView,
} from '@/app/types';
import {
  buildSessionId,
  emptySessionCatalog,
  getActiveSession,
  readSessionCatalog,
  removeSession,
  setActiveSessionId,
  updateSessionSelection as persistSessionSelection,
  upsertSession,
} from '@/shared/storage';

interface AuthContextValue {
  session: SessionState | null;
  sessions: SessionState[];
  activeSessionId: string | null;
  isLoading: boolean;
  signInAsGuest: (workspaceId?: string) => Promise<SessionState>;
  signIn: (payload: LoginRequest) => Promise<SessionState>;
  switchSession: (sessionId: string) => Promise<SessionState>;
  signOut: () => void;
  updateSessionSelection: (selection: {
    lastStoryId?: string | null;
    lastRunId?: string | null;
    lastView?: StorySurfaceView;
  }) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function normalizeWorkspaceSummary(
  payload:
    | LoginResponse['active_workspace']
    | GuestSessionResponse['active_workspace']
    | undefined,
  fallback: {
    workspaceId: string;
    workspaceKind: SessionState['kind'] | 'unknown';
    label: string;
    persistence: ActiveWorkspaceSummary['persistence'];
    summary: string;
  },
): ActiveWorkspaceSummary {
  return {
    workspaceId: payload?.workspace_id ?? fallback.workspaceId,
    workspaceKind: payload?.workspace_kind ?? fallback.workspaceKind,
    label: payload?.label ?? fallback.label,
    persistence: payload?.persistence ?? fallback.persistence,
    summary: payload?.summary ?? fallback.summary,
  };
}

function buildGuestSession(
  response: GuestSessionResponse,
  previous?: SessionState | null,
): SessionState {
  const workspaceId = response.workspace_id;
  return {
    id: buildSessionId({ kind: 'guest', workspaceId }),
    kind: 'guest',
    identityKind: response.identity_kind ?? 'guest',
    workspaceId,
    activeWorkspace: normalizeWorkspaceSummary(response.active_workspace, {
      workspaceId,
      workspaceKind: response.workspace_kind ?? 'guest',
      label: 'Guest workspace',
      persistence: 'ephemeral',
      summary: 'Disposable workspace for drafting and flow verification.',
    }),
    lastStoryId: previous?.lastStoryId ?? null,
    lastRunId: previous?.lastRunId ?? null,
    lastView: previous?.lastView ?? 'workspace',
    createdAt: previous?.createdAt,
    updatedAt: new Date().toISOString(),
  };
}

function buildUserSessionFromLogin(
  response: LoginResponse,
  previous?: SessionState | null,
): SessionState {
  const workspaceId = response.workspace_id;
  return {
    id: buildSessionId({ kind: 'user', workspaceId }),
    kind: 'user',
    identityKind: response.identity_kind ?? 'user',
    workspaceId,
    token: response.access_token,
    refreshToken: response.refresh_token,
    user: response.user,
    activeWorkspace: normalizeWorkspaceSummary(response.active_workspace, {
      workspaceId,
      workspaceKind: response.workspace_kind ?? 'user',
      label: 'Signed-in workspace',
      persistence: 'persistent',
      summary: 'Stable author workspace bound to the authenticated identity.',
    }),
    lastStoryId: previous?.lastStoryId ?? null,
    lastRunId: previous?.lastRunId ?? null,
    lastView: previous?.lastView ?? 'workspace',
    createdAt: previous?.createdAt,
    updatedAt: new Date().toISOString(),
  };
}

function buildUserSessionFromCurrentUser(
  user: CurrentUserResponse,
  previous: SessionState,
): SessionState {
  const workspaceId = `user-${user.username}`;
  return {
    id: buildSessionId({ kind: 'user', workspaceId }),
    kind: 'user',
    identityKind: 'user',
    workspaceId,
    token: previous.token,
    refreshToken: previous.refreshToken,
    user: {
      id: user.id,
      name: user.username,
      email: user.email,
    },
    activeWorkspace: {
      workspaceId,
      workspaceKind: 'user',
      label: 'Signed-in workspace',
      persistence: 'persistent',
      summary: 'Stable author workspace bound to the authenticated identity.',
    },
    lastStoryId: previous.lastStoryId ?? null,
    lastRunId: previous.lastRunId ?? null,
    lastView: previous.lastView ?? 'workspace',
    createdAt: previous.createdAt,
    updatedAt: new Date().toISOString(),
  };
}

async function validateStoredSession(session: SessionState): Promise<SessionState> {
  if (session.kind === 'guest') {
    const response = await api.createGuestSession({
      workspace_id: session.workspaceId,
    });
    return buildGuestSession(response, session);
  }

  if (!session.token) {
    throw new Error('Stored user session is missing its access token.');
  }

  const user = await api.getCurrentUser(session.token);
  return buildUserSessionFromCurrentUser(user, session);
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [catalog, setCatalog] = useState<SessionCatalog>(emptySessionCatalog());
  const [isLoading, setIsLoading] = useState(true);
  const catalogRef = useRef<SessionCatalog>(catalog);

  useEffect(() => {
    catalogRef.current = catalog;
  }, [catalog]);

  useEffect(() => {
    let isCancelled = false;

    async function restoreSessionCatalog() {
      const storedCatalog = readSessionCatalog();
      if (isCancelled) {
        return;
      }

      setCatalog(storedCatalog);
      const activeSession = getActiveSession(storedCatalog);
      if (!activeSession) {
        setIsLoading(false);
        return;
      }

      try {
        const validatedSession = await validateStoredSession(activeSession);
        if (isCancelled) {
          return;
        }
        const nextCatalog = upsertSession(storedCatalog, validatedSession);
        setCatalog(nextCatalog);
      } catch {
        if (isCancelled) {
          return;
        }
        const nextCatalog = removeSession(storedCatalog, activeSession.id);
        setCatalog(nextCatalog);
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    void restoreSessionCatalog();

    return () => {
      isCancelled = true;
    };
  }, []);

  const session = getActiveSession(catalog);

  const signInAsGuest = async (workspaceId?: string) => {
    const previous =
      catalogRef.current.sessions.find(
        (entry) => entry.kind === 'guest' && entry.workspaceId === workspaceId,
      ) ?? null;
    const response = await api.createGuestSession(
      workspaceId ? { workspace_id: workspaceId } : undefined,
    );
    const nextSession = buildGuestSession(response, previous);
    const nextCatalog = upsertSession(catalogRef.current, nextSession);
    setCatalog(nextCatalog);
    return nextSession;
  };

  const signIn = async (payload: LoginRequest) => {
    const response = await api.login(payload);
    const previous =
      catalogRef.current.sessions.find(
        (entry) => entry.kind === 'user' && entry.workspaceId === response.workspace_id,
      ) ?? null;
    const nextSession = buildUserSessionFromLogin(response, previous);
    const nextCatalog = upsertSession(catalogRef.current, nextSession);
    setCatalog(nextCatalog);
    return nextSession;
  };

  const switchSession = async (sessionId: string) => {
    const targetSession = catalogRef.current.sessions.find(
      (entry) => entry.id === sessionId,
    );
    if (!targetSession) {
      throw new Error('Saved session not found.');
    }

    const previousCatalog = catalogRef.current;
    const optimisticCatalog = setActiveSessionId(previousCatalog, targetSession.id);
    setCatalog(optimisticCatalog);

    try {
      const validatedSession = await validateStoredSession(targetSession);
      const nextCatalog = upsertSession(readSessionCatalog(), validatedSession);
      setCatalog(nextCatalog);
      return validatedSession;
    } catch (error) {
      const rollbackCatalog = setActiveSessionId(
        readSessionCatalog(),
        previousCatalog.activeSessionId,
      );
      setCatalog(rollbackCatalog);
      throw error;
    }
  };

  const signOut = () => {
    const activeSession = getActiveSession(catalogRef.current);
    if (!activeSession) {
      return;
    }
    const nextCatalog = removeSession(catalogRef.current, activeSession.id);
    setCatalog(nextCatalog);
  };

  const updateSessionSelection = (selection: {
    lastStoryId?: string | null;
    lastRunId?: string | null;
    lastView?: StorySurfaceView;
  }) => {
    const activeSession = getActiveSession(catalogRef.current);
    if (!activeSession) {
      return;
    }

    const nextCatalog = persistSessionSelection(catalogRef.current, activeSession.id, {
      lastStoryId: selection.lastStoryId ?? activeSession.lastStoryId ?? null,
      lastRunId: selection.lastRunId ?? activeSession.lastRunId ?? null,
      lastView: selection.lastView ?? activeSession.lastView ?? 'workspace',
    });
    setCatalog(nextCatalog);
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        sessions: catalog.sessions,
        activeSessionId: catalog.activeSessionId,
        isLoading,
        signInAsGuest,
        signIn,
        switchSession,
        signOut,
        updateSessionSelection,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
