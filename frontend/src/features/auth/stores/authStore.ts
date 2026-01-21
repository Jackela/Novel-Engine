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
      initialize: async () => {
        const state = get();
        if (state.isInitialized) return;

        set({ isLoading: true });

        try {
          // Check for existing token
          if (state.token) {
            // Validate token hasn't expired
            if (state.token.expiresAt > Date.now()) {
              set({ isAuthenticated: true, isInitialized: true, isLoading: false });
              return;
            }

            // Try to refresh if we have a refresh token
            if (state.token.refreshToken && state.token.refreshExpiresAt > Date.now()) {
              try {
                const newToken = await authAPI.refreshToken(state.token.refreshToken);
                set({
                  token: newToken,
                  isAuthenticated: true,
                  isInitialized: true,
                  isLoading: false,
                });
                return;
              } catch {
                // Refresh failed, continue to signed out state
              }
            }
          }

          // Check for guest session
          if (typeof window !== 'undefined') {
            const hasGuestSession = localStorage.getItem(GUEST_SESSION_KEY) === '1';
            if (hasGuestSession) {
              try {
                const session = await authAPI.createGuestSession();
                set({
                  isAuthenticated: true,
                  isGuest: true,
                  token: createGuestToken(),
                  workspaceId: session.workspace_id,
                  isInitialized: true,
                  isLoading: false,
                });
                return;
              } catch {
                // Guest session failed, continue to signed out state
              }
            }
          }

          // No valid auth found
          set({
            isAuthenticated: false,
            isGuest: false,
            token: null,
            isInitialized: true,
            isLoading: false,
          });
        } catch (error) {
          set({
            isAuthenticated: false,
            token: null,
            error: error as Error,
            isInitialized: true,
            isLoading: false,
          });
        }
      },

      // Login
      login: async (credentials) => {
        set({ isLoading: true, error: null });

        try {
          const token = await authAPI.login(credentials);
          set({
            token,
            isAuthenticated: true,
            isGuest: false,
            workspaceId: null,
            isLoading: false,
          });
        } catch (error) {
          set({
            isAuthenticated: false,
            token: null,
            error: error as Error,
            isLoading: false,
          });
          throw error;
        }
      },

      // Logout
      logout: async () => {
        const state = get();
        set({ isLoading: true });

        try {
          if (state.isGuest) {
            // Clear guest session
            if (typeof window !== 'undefined') {
              localStorage.removeItem(GUEST_SESSION_KEY);
            }
          } else {
            // Call logout API
            await authAPI.logout();
          }

          set({
            isAuthenticated: false,
            isGuest: false,
            token: null,
            workspaceId: null,
            isLoading: false,
          });
        } catch (error) {
          set({ error: error as Error, isLoading: false });
          throw error;
        }
      },

      // Enter guest mode
      enterGuestMode: async () => {
        set({ isLoading: true, error: null });

        try {
          const session = await authAPI.createGuestSession();

          if (typeof window !== 'undefined') {
            localStorage.setItem(GUEST_SESSION_KEY, '1');
          }

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
      },

      // Refresh token
      refreshToken: async () => {
        const state = get();
        if (!state.token?.refreshToken) {
          throw new Error('No refresh token available');
        }

        set({ isLoading: true });

        try {
          const newToken = await authAPI.refreshToken(state.token.refreshToken);
          set({ token: newToken, isLoading: false });
        } catch (error) {
          set({
            isAuthenticated: false,
            token: null,
            error: error as Error,
            isLoading: false,
          });
          throw error;
        }
      },

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
