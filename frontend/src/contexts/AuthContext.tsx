/**
 * AuthContext - Global Authentication State Provider
 * 
 * React Context for managing authentication state across the application
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Adapter layer for React component tree
 * - Article IV (SSOT): Single source of truth for auth state
 * - Article V (SOLID): SRP - Manages only auth context
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import type { LoginRequest, AuthToken } from '../types/auth';
import type { IAuthenticationService } from '../services/auth/IAuthenticationService';
import { JWTAuthService } from '../services/auth/JWTAuthService';
import { TokenStorage } from '../services/auth/TokenStorage';
// import { createAuthenticatedAPIClient } from '../services/api/apiClient'; // Available for future use
import axios from 'axios';
import { logger } from '../services/logging/LoggerFactory';

const createGuestToken = (): AuthToken => {
  const now = Date.now();
  return {
    accessToken: 'guest-access-token',
    refreshToken: 'guest-refresh-token',
    tokenType: 'guest',
    expiresAt: now + 3600 * 1000,
    refreshExpiresAt: now + 24 * 3600 * 1000,
    user: {
      id: 'guest-user',
      username: 'Guest Explorer',
      email: 'guest@example.com',
      roles: ['guest'],
    },
  };
};

const GUEST_SESSION_KEY = 'novel-engine-guest-session';

/**
 * Authentication context state
 */
interface AuthContextState {
  isAuthenticated: boolean;
  isGuest: boolean;
  token: AuthToken | null;
  isLoading: boolean;
  error: Error | null;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  enterGuestMode: () => void;
}

interface AuthInternalState {
  isAuthenticated: boolean;
  isGuest: boolean;
  token: AuthToken | null;
  isLoading: boolean;
  error: Error | null;
}

/**
 * AuthContext with default values
 */
const AuthContext = createContext<AuthContextState | undefined>(undefined);

/**
 * AuthProvider Props
 */
interface AuthProviderProps {
  children: React.ReactNode;
  authService?: IAuthenticationService; // Optional for testing
}

/**
 * AuthProvider Component
 * 
 * Provides authentication state and actions to the entire application
 * 
 * @param props - Component props
 * @returns Provider component wrapping children
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({ children, authService: customAuthService }) => {
  const enableGuestMode =
    String(
      (import.meta.env.VITE_ENABLE_GUEST_MODE ??
        process.env.REACT_APP_ENABLE_GUEST_MODE ??
        'true') as string
    )
      .trim()
      .toLowerCase() === 'true';

  // Initialize auth service (use custom or create default)
  const [authService] = useState<IAuthenticationService>(() => {
    if (customAuthService) {
      return customAuthService;
    }

    // Create default auth service
    const tokenStorage = new TokenStorage();
    const httpClient = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
      timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || process.env.REACT_APP_API_TIMEOUT || '10000'),
    });

    return new JWTAuthService(httpClient, tokenStorage);
  });

  // Auth state
  const [state, setState] = useState<AuthInternalState>({
    isAuthenticated: false,
    isGuest: false,
    token: null,
    isLoading: true,
    error: null,
  });

  /**
   * Initialize auth state from storage on mount
   */
  useEffect(() => {
    const initializeAuth = async () => {
      const shouldResumeGuestSession = (() => {
        if (!enableGuestMode || typeof window === 'undefined') {
          return false;
        }
        try {
          return window.sessionStorage.getItem(GUEST_SESSION_KEY) === '1';
        } catch {
          return false;
        }
      })();

      try {
        logger.info('Initializing authentication state', {
          component: 'AuthProvider',
          action: 'initialize',
        });

        const isAuth = await authService.isAuthenticated();
        const token = authService.getToken();

        if (isAuth) {
          setState({
            isAuthenticated: true,
            isGuest: false,
            token,
            isLoading: false,
            error: null,
          });
        } else if (shouldResumeGuestSession) {
          setState({
            isAuthenticated: true,
            isGuest: true,
            token: createGuestToken(),
            isLoading: false,
            error: null,
          });
        } else {
          setState({
            isAuthenticated: false,
            isGuest: false,
            token: null,
            isLoading: false,
            error: null,
          });
        }

        // Start automatic token refresh if authenticated
        if (isAuth) {
          authService.startTokenRefresh();
          logger.info('User authenticated, token refresh started', {
            component: 'AuthProvider',
            action: 'initialize',
            ...(token?.user.id ? { userId: token.user.id } : {}),
          });
        } else if (!enableGuestMode) {
          logger.info('User not authenticated', {
            component: 'AuthProvider',
            action: 'initialize',
          });
        }
      } catch (error) {
        logger.error('Failed to initialize auth state', error as Error, {
          component: 'AuthProvider',
          action: 'initialize',
        });

        if (enableGuestMode && shouldResumeGuestSession) {
          setState({
            isAuthenticated: true,
            isGuest: true,
            token: createGuestToken(),
            isLoading: false,
            error: null,
          });
        } else {
          setState({
            isAuthenticated: false,
            isGuest: false,
            token: null,
            isLoading: false,
            error: error as Error,
          });
        }
      }
    };

    initializeAuth();
  }, [authService, enableGuestMode]);

  /**
   * Subscribe to auth state changes
   */
  useEffect(() => {
    const unsubscribe = authService.onAuthStateChange((authState) => {
      logger.debug('Auth state changed', {
        component: 'AuthProvider',
        action: 'stateChange',
        isAuthenticated: authState.isAuthenticated,
      });

      if (authState.isAuthenticated) {
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          isGuest: false,
          token: authService.getToken(),
        }));
      } else if (enableGuestMode) {
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          isGuest: true,
          token: createGuestToken(),
        }));
      } else {
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          isGuest: false,
          token: null,
        }));
      }
    });

    return () => {
      unsubscribe();
    };
  }, [authService]);

  /**
   * Register unauthenticated callback for redirect
   */
  useEffect(() => {
    if (!enableGuestMode) {
      authService.onUnauthenticated(() => {
        logger.warn('User became unauthenticated, redirecting to login', {
          component: 'AuthProvider',
          action: 'unauthenticated',
        });

        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
      });
    }
  }, [authService, enableGuestMode]);

  /**
   * Login with credentials
   */
  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      logger.info('Login attempt', {
        component: 'AuthProvider',
        action: 'login',
        username: credentials.username,
      });

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const token = await authService.login(credentials);

      setState({
        isAuthenticated: true,
        isGuest: false,
        token,
        isLoading: false,
        error: null,
      });

      logger.info('Login successful', {
        component: 'AuthProvider',
        action: 'login',
        userId: token.user.id,
      });
    } catch (error) {
      logger.error('Login failed', error as Error, {
        component: 'AuthProvider',
        action: 'login',
        username: credentials.username,
      });

      setState({
        isAuthenticated: false,
        isGuest: false,
        token: null,
        isLoading: false,
        error: error as Error,
      });

      throw error;
    }
  };

  /**
   * Logout
   */
  const logout = async (): Promise<void> => {
    try {
      logger.info('Logout attempt', {
        component: 'AuthProvider',
        action: 'logout',
      });

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      if (state.isGuest && enableGuestMode) {
        if (typeof window !== 'undefined') {
          try {
            window.sessionStorage.removeItem(GUEST_SESSION_KEY);
          } catch {
            // ignore
          }
        }
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          isGuest: false,
          token: null,
          isLoading: false,
          error: null,
        }));
        if (typeof window !== 'undefined') {
          window.location.href = '/';
        }
        return;
      } else {
        await authService.logout();
        setState({
          isAuthenticated: false,
          isGuest: false,
          token: null,
          isLoading: false,
          error: null,
        });
      }

      logger.info('Logout successful', {
        component: 'AuthProvider',
        action: 'logout',
      });
    } catch (error) {
      logger.error('Logout failed', error as Error, {
        component: 'AuthProvider',
        action: 'logout',
      });

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error as Error,
      }));

      throw error;
    }
  };

  /**
   * Manually refresh token
   */
  const refreshToken = async (): Promise<void> => {
    try {
      logger.info('Manual token refresh', {
        component: 'AuthProvider',
        action: 'refreshToken',
      });

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const token = await authService.refreshToken();

      setState({
        isAuthenticated: true,
        isGuest: false,
        token,
        isLoading: false,
        error: null,
      });

      logger.info('Token refresh successful', {
        component: 'AuthProvider',
        action: 'refreshToken',
      });
    } catch (error) {
      logger.error('Token refresh failed', error as Error, {
        component: 'AuthProvider',
        action: 'refreshToken',
      });

      setState({
        isAuthenticated: false,
        isGuest: false,
        token: null,
        isLoading: false,
        error: error as Error,
      });

      throw error;
    }
  };

  const enterGuestMode = () => {
    if (!enableGuestMode) {
      logger.warn('Guest mode is disabled; ignoring enterGuestMode call');
      return;
    }

    if (typeof window !== 'undefined') {
      try {
        window.sessionStorage.setItem(GUEST_SESSION_KEY, '1');
      } catch {
        // ignore
      }
    }

    setState({
      isAuthenticated: true,
      isGuest: true,
      token: createGuestToken(),
      isLoading: false,
      error: null,
    });
  };

  const contextValue: AuthContextState = {
    ...state,
    login,
    logout,
    refreshToken,
    enterGuestMode,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * useAuthContext Hook
 * 
 * Access authentication context from components
 * 
 * @returns Authentication context state and actions
 * @throws Error if used outside AuthProvider
 */
export const useAuthContext = (): AuthContextState => {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }

  return context;
};
