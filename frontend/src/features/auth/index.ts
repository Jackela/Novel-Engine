/**
 * Auth Feature Module
 * Exports auth stores, hooks, and components
 */

// Store
export { useAuthStore } from './stores/authStore';
export {
  useIsAuthenticated,
  useIsGuest,
  useAuthLoading,
  useAuthUser,
  useAuthError,
} from './stores/authStore';

// Hooks
export { useAuth, useRequireAuth, useCurrentUser, useHasRole } from './hooks/useAuth';
