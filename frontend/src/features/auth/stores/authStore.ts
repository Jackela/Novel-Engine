/**
 * Auth Store (Zustand)
 * Manages authentication state with persistence
 */
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { AuthToken, LoginRequest, LoginResponse } from '@/types/auth';
import { AuthResponseSchema } from '@/types/schemas';

const AUTH_STORAGE_KEY = 'novel-engine-auth';
const GUEST_SESSION_KEY = 'novelengine_guest_session';

interface AuthState {
  // State
  isAuthenticated: boolean;
  isGuest: boolean;
  isLoading: boolean;
  isInitialized: boolean;
  token: AuthToken | null;
  workspaceId: string | null;
  error: Error | null;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  enterGuestMode: () => Promise<void>;
  refreshToken: () => Promise<void>;
  clearError: () => void;
  initialize: () => Promise<void>;
}

const getGuestSessionFlag = () =>
  typeof window !== 'undefined' && localStorage.getItem(GUEST_SESSION_KEY) === '1';

const setGuestSessionFlag = (value: boolean) => {
  if (typeof window === 'undefined') {
    return;
  }
  if (value) {
    localStorage.setItem(GUEST_SESSION_KEY, '1');
  } else {
    localStorage.removeItem(GUEST_SESSION_KEY);
  }
};

const setSignedOutState = (set: (state: Partial<AuthState>) => void) => {
  set({
    isAuthenticated: false,
    isGuest: false,
    token: null,
    workspaceId: null,
    isInitialized: true,
    isLoading: false,
  });
};

const setAuthLoading = (
  set: (state: Partial<AuthState>) => void,
  isLoading: boolean
) => {
  set({ isLoading });
};

const setAuthError = (set: (state: Partial<AuthState>) => void, error: Error) => {
  set({
    isAuthenticated: false,
    token: null,
    error,
    isLoading: false,
  });
};

const applyTokenState = (
  set: (state: Partial<AuthState>) => void,
  token: AuthToken,
  extra?: Partial<AuthState>
) => {
  set({
    token,
    isAuthenticated: true,
    isGuest: false,
    isLoading: false,
    ...extra,
  });
};

const tryRestoreToken = async (
  state: AuthState,
  set: (state: Partial<AuthState>) => void
) => {
  if (!state.token) {
    return false;
  }
  if (state.token.expiresAt > Date.now()) {
    applyTokenState(set, state.token, { isInitialized: true });
    return true;
  }
  if (state.token.refreshToken && state.token.refreshExpiresAt > Date.now()) {
    const newToken = await authAPI.refreshToken(state.token.refreshToken);
    applyTokenState(set, newToken, { isInitialized: true });
    return true;
  }
  return false;
};

const tryRestoreGuestSession = async (set: (state: Partial<AuthState>) => void) => {
  if (!getGuestSessionFlag()) {
    return false;
  }
  const session = await authAPI.createGuestSession();
  set({
    isAuthenticated: true,
    isGuest: true,
    token: createGuestToken(),
    workspaceId: session.workspace_id,
    isInitialized: true,
    isLoading: false,
  });
  return true;
};

const createInitialize =
  (set: (state: Partial<AuthState>) => void, get: () => AuthState) => async () => {
    const state = get();
    if (state.isInitialized) return;

    setAuthLoading(set, true);

    try {
      if (await tryRestoreToken(state, set)) {
        return;
      }
      if (await tryRestoreGuestSession(set)) {
        return;
      }
      setSignedOutState(set);
    } catch (error) {
      set({
        isAuthenticated: false,
        token: null,
        error: error as Error,
        isInitialized: true,
        isLoading: false,
      });
    }
  };

const createLogin =
  (set: (state: Partial<AuthState>) => void) => async (credentials: LoginRequest) => {
    set({ isLoading: true, error: null });

    try {
      const token = await authAPI.login(credentials);
      applyTokenState(set, token, { workspaceId: null });
    } catch (error) {
      setAuthError(set, error as Error);
      throw error;
    }
  };

const createLogout =
  (set: (state: Partial<AuthState>) => void, get: () => AuthState) => async () => {
    const state = get();
    setAuthLoading(set, true);

    try {
      if (state.isGuest) {
        setGuestSessionFlag(false);
      } else {
        await authAPI.logout();
      }

      setSignedOutState(set);
    } catch (error) {
      set({ error: error as Error, isLoading: false });
      throw error;
    }
  };

const createGuestMode = (set: (state: Partial<AuthState>) => void) => async () => {
  set({ isLoading: true, error: null });

  try {
    const session = await authAPI.createGuestSession();
    setGuestSessionFlag(true);

    set({
      isAuthenticated: true,
      isGuest: true,
      token: createGuestToken(),
      workspaceId: session.workspace_id,
      isLoading: false,
    });
  } catch (error) {
    set({
      isAuthenticated: false,
      error: error as Error,
      isLoading: false,
    });
    throw error;
  }
};

const createRefreshToken =
  (set: (state: Partial<AuthState>) => void, get: () => AuthState) => async () => {
    const state = get();
    if (!state.token?.refreshToken) {
      throw new Error('No refresh token available');
    }

    setAuthLoading(set, true);

    try {
      const newToken = await authAPI.refreshToken(state.token.refreshToken);
      set({ token: newToken, isLoading: false });
    } catch (error) {
      setAuthError(set, error as Error);
      throw error;
    }
  };

// API helper functions
const authAPI = {
  login: async (credentials: LoginRequest): Promise<AuthToken> => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }

    const data = AuthResponseSchema.parse(await response.json());
    return transformLoginResponse(data);
  },

  logout: async (): Promise<void> => {
    await fetch('/api/auth/logout', { method: 'POST' });
  },

  refreshToken: async (refreshToken: string): Promise<AuthToken> => {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    const data = AuthResponseSchema.parse(await response.json());
    return transformLoginResponse(data);
  },

  createGuestSession: async (): Promise<{ workspace_id: string }> => {
    const response = await fetch('/api/guest/sessions', { method: 'POST' });
    if (!response.ok) {
      throw new Error('Failed to create guest session');
    }
    return response.json();
  },
};

// Transform API response to AuthToken
function transformLoginResponse(data: LoginResponse): AuthToken {
  const expiresIn = data.expires_in || 3600;
  const refreshExpiresIn = data.refresh_expires_in || 86400;

  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    tokenType: data.token_type || 'Bearer',
    expiresAt: Date.now() + expiresIn * 1000,
    refreshExpiresAt: Date.now() + refreshExpiresIn * 1000,
    user: data.user,
  };
}

// Create guest token
function createGuestToken(): AuthToken {
  return {
    accessToken: 'guest',
    refreshToken: '',
    tokenType: 'Guest',
    expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    refreshExpiresAt: 0,
    user: {
      id: 'guest',
      username: 'guest',
      email: '',
      roles: ['guest'],
    },
  };
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      isAuthenticated: false,
      isGuest: false,
      isLoading: false,
      isInitialized: false,
      token: null,
      workspaceId: null,
      error: null,

      // Initialize auth state
      initialize: createInitialize(set, get),

      // Login
      login: createLogin(set),

      // Logout
      logout: createLogout(set, get),

      // Enter guest mode
      enterGuestMode: createGuestMode(set),

      // Refresh token
      refreshToken: createRefreshToken(set, get),

      // Clear error
      clearError: () => set({ error: null }),
    }),
    {
      name: AUTH_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        isGuest: state.isGuest,
        workspaceId: state.workspaceId,
      }),
    }
  )
);

// Selector hooks for common use cases
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useIsGuest = () => useAuthStore((state) => state.isGuest);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthUser = () => useAuthStore((state) => state.token?.user ?? null);
export const useAuthError = () => useAuthStore((state) => state.error);
