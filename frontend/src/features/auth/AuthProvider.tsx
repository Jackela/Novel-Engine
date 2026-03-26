import {
  createContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react';

import { api } from '@/app/api';
import type { LoginRequest, SessionState } from '@/app/types';
import { sessionStorageKey, safeStorage } from '@/shared/storage';

interface AuthContextValue {
  session: SessionState | null;
  isLoading: boolean;
  signInAsGuest: () => Promise<SessionState>;
  signIn: (payload: LoginRequest) => Promise<SessionState>;
  signOut: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function buildGuestSession(workspaceId: string): SessionState {
  return {
    kind: 'guest',
    workspaceId,
  };
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<SessionState | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setSession(safeStorage.read<SessionState>(sessionStorageKey));
    setIsLoading(false);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isLoading,
      async signInAsGuest() {
        const response = await api.createGuestSession();
        if (!response.workspace_id) {
          throw new Error('Guest session response missing workspace_id');
        }
        const nextSession = buildGuestSession(response.workspace_id);
        safeStorage.write(sessionStorageKey, nextSession);
        setSession(nextSession);
        return nextSession;
      },
      async signIn(payload) {
        const response = await api.login(payload);
        if (!response.workspace_id) {
          throw new Error('Login response missing workspace_id');
        }
        if (!response.user) {
          throw new Error('Login response missing user profile');
        }
        const nextSession: SessionState = {
          kind: 'user',
          workspaceId: response.workspace_id,
          token: response.access_token,
          refreshToken: response.refresh_token,
          user: response.user,
        };

        safeStorage.write(sessionStorageKey, nextSession);
        setSession(nextSession);
        return nextSession;
      },
      signOut() {
        safeStorage.remove(sessionStorageKey);
        setSession(null);
      },
    }),
    [isLoading, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
