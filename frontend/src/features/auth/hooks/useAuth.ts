/**
 * Auth Hooks
 * Convenience hooks for authentication
 */
import { useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';

/**
 * Main auth hook - provides all auth state and actions
 */
export function useAuth() {
  const store = useAuthStore();
  const { isInitialized, isLoading, initialize } = store;

  useEffect(() => {
    if (!isInitialized && !isLoading) {
      initialize();
    }
  }, [initialize, isInitialized, isLoading]);

  return {
    // State
    isAuthenticated: store.isAuthenticated,
    isGuest: store.isGuest,
    isLoading: store.isLoading,
    isInitialized: store.isInitialized,
    user: store.token?.user ?? null,
    error: store.error,

    // Actions
    login: store.login,
    logout: store.logout,
    loginAsGuest: store.enterGuestMode,
    enterGuestMode: store.enterGuestMode,
    refreshToken: store.refreshToken,
    clearError: store.clearError,
  };
}

/**
 * Hook to require authentication
 * Returns true if authenticated, false if not
 * Use with router guards
 */
export function useRequireAuth(): boolean {
  const { isAuthenticated, isInitialized, isLoading } = useAuth();

  // Still loading
  if (!isInitialized || isLoading) {
    return false;
  }

  return isAuthenticated;
}

/**
 * Hook to get current user
 */
export function useCurrentUser() {
  return useAuthStore((state) => state.token?.user ?? null);
}

/**
 * Hook to check if user has specific role
 */
export function useHasRole(role: string): boolean {
  const user = useCurrentUser();
  return user?.roles.includes(role) ?? false;
}
