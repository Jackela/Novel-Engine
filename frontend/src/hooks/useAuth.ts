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

const setAuthenticatedState = (
  setState: React.Dispatch<React.SetStateAction<UseAuthState>>,
  isAuthenticated: boolean,
  token: AuthToken | null
) => {
  setState({
    isAuthenticated,
    token,
    isLoading: false,
    error: null,
  });
};

const setLoadingState = (
  setState: React.Dispatch<React.SetStateAction<UseAuthState>>
) => {
  setState(prev => ({ ...prev, isLoading: true, error: null }));
};

const setErrorState = (
  setState: React.Dispatch<React.SetStateAction<UseAuthState>>,
  error: Error,
  isAuthenticated = false
) => {
  setState({
    isAuthenticated,
    token: null,
    isLoading: false,
    error,
  });
};

const useInitializeAuth = (
  authService: IAuthenticationService,
  setState: React.Dispatch<React.SetStateAction<UseAuthState>>
) => {
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const isAuth = await authService.isAuthenticated();
        const token = authService.getToken();

        setAuthenticatedState(setState, isAuth, token);

        if (isAuth) {
          authService.startTokenRefresh();
        }
      } catch (error) {
        setErrorState(setState, error as Error);
      }
    };

    initializeAuth();
  }, [authService, setState]);
};

const useAuthStateSubscription = (
  authService: IAuthenticationService,
  setState: React.Dispatch<React.SetStateAction<UseAuthState>>
) => {
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
  }, [authService, setState]);
};

const useAuthActions = (
  authService: IAuthenticationService,
  setState: React.Dispatch<React.SetStateAction<UseAuthState>>
) => {
  const login = useCallback(async (credentials: LoginRequest): Promise<void> => {
    try {
      setLoadingState(setState);
      const token = await authService.login(credentials);
      setAuthenticatedState(setState, true, token);
    } catch (error) {
      setErrorState(setState, error as Error);
      throw error;
    }
  }, [authService, setState]);

  const logout = useCallback(async (): Promise<void> => {
    try {
      setLoadingState(setState);
      await authService.logout();
      setAuthenticatedState(setState, false, null);
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error as Error,
      }));
      throw error;
    }
  }, [authService, setState]);

  const refreshToken = useCallback(async (): Promise<void> => {
    try {
      setLoadingState(setState);
      const token = await authService.refreshToken();
      setAuthenticatedState(setState, true, token);
    } catch (error) {
      setErrorState(setState, error as Error);
      throw error;
    }
  }, [authService, setState]);

  return { login, logout, refreshToken };
};

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

  useInitializeAuth(authService, setState);
  useAuthStateSubscription(authService, setState);
  const { login, logout, refreshToken } = useAuthActions(authService, setState);

  return {
    ...state,
    login,
    logout,
    refreshToken,
  };
};
