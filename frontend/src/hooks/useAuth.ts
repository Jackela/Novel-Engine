/**
 * useAuth React Hook
 * 
 * Custom hook for authentication state management
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Adapter layer for React components
 * - Article IV (SSOT): Single source for auth state in components
 * - Article V (SOLID): SRP - Manages only auth state in React
 */

import { useState, useEffect, useCallback } from 'react';
import type { LoginRequest, AuthToken } from '@/types/auth';
import type { IAuthenticationService } from '@/services/auth/IAuthenticationService';

/**
 * Authentication state interface
 */
export interface UseAuthState {
  isAuthenticated: boolean;
  token: AuthToken | null;
  isLoading: boolean;
  error: Error | null;
}

/**
 * useAuth hook return type
 */
export interface UseAuthReturn extends UseAuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

/**
 * useAuth hook
 * 
 * Provides authentication state and actions to React components
 * 
 * @param authService - Authentication service instance
 * @returns Authentication state and actions
 */
export const useAuth = (authService: IAuthenticationService): UseAuthReturn => {
  const [state, setState] = useState<UseAuthState>({
    isAuthenticated: false,
    token: null,
    isLoading: true,
    error: null,
  });

  /**
   * Initialize auth state from storage
   */
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const isAuth = await authService.isAuthenticated();
        const token = authService.getToken();

        setState({
          isAuthenticated: isAuth,
          token,
          isLoading: false,
          error: null,
        });

        // Start automatic token refresh if authenticated
        if (isAuth) {
          authService.startTokenRefresh();
        }
      } catch (error) {
        setState({
          isAuthenticated: false,
          token: null,
          isLoading: false,
          error: error as Error,
        });
      }
    };

    initializeAuth();
  }, [authService]);

  /**
   * Subscribe to auth state changes
   */
  useEffect(() => {
    const unsubscribe = authService.onAuthStateChange((authState) => {
      setState(prev => ({
        ...prev,
        isAuthenticated: authState.isAuthenticated,
        token: authState.isAuthenticated ? authService.getToken() : null,
      }));
    });

    return () => {
      unsubscribe();
    };
  }, [authService]);

  /**
   * Login with credentials
   */
  const login = useCallback(async (credentials: LoginRequest): Promise<void> => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const token = await authService.login(credentials);

      setState({
        isAuthenticated: true,
        token,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setState({
        isAuthenticated: false,
        token: null,
        isLoading: false,
        error: error as Error,
      });
      throw error;
    }
  }, [authService]);

  /**
   * Logout
   */
  const logout = useCallback(async (): Promise<void> => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      await authService.logout();

      setState({
        isAuthenticated: false,
        token: null,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error as Error,
      }));
      throw error;
    }
  }, [authService]);

  /**
   * Manually refresh token
   */
  const refreshToken = useCallback(async (): Promise<void> => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const token = await authService.refreshToken();

      setState({
        isAuthenticated: true,
        token,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setState({
        isAuthenticated: false,
        token: null,
        isLoading: false,
        error: error as Error,
      });
      throw error;
    }
  }, [authService]);

  return {
    ...state,
    login,
    logout,
    refreshToken,
  };
};
