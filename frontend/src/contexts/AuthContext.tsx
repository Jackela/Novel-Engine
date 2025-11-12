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

/**
 * Authentication context state
 */
interface AuthContextState {
  isAuthenticated: boolean;
  token: AuthToken | null;
  isLoading: boolean;
  error: Error | null;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
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
  // Initialize auth service (use custom or create default)
  const [authService] = useState<IAuthenticationService>(() => {
    if (customAuthService) {
      return customAuthService;
    }

    // Create default auth service
    const tokenStorage = new TokenStorage();
    const httpClient = axios.create({
      baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
      timeout: parseInt(process.env.REACT_APP_API_TIMEOUT || '10000'),
    });

    return new JWTAuthService(httpClient, tokenStorage);
  });

  // Auth state
  const [state, setState] = useState<Omit<AuthContextState, 'login' | 'logout' | 'refreshToken'>>({
    isAuthenticated: false,
    token: null,
    isLoading: true,
    error: null,
  });

  /**
   * Initialize auth state from storage on mount
   */
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        logger.info('Initializing authentication state', undefined, {
          component: 'AuthProvider',
          action: 'initialize',
        });

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
          logger.info('User authenticated, token refresh started', undefined, {
            component: 'AuthProvider',
            action: 'initialize',
            userId: token?.user.id,
          });
        } else {
          logger.info('User not authenticated', undefined, {
            component: 'AuthProvider',
            action: 'initialize',
          });
        }
      } catch (error) {
        logger.error('Failed to initialize auth state', error as Error, {
          component: 'AuthProvider',
          action: 'initialize',
        });

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
      logger.debug('Auth state changed', undefined, {
        component: 'AuthProvider',
        action: 'stateChange',
        isAuthenticated: authState.isAuthenticated,
      });

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
   * Register unauthenticated callback for redirect
   */
  useEffect(() => {
    authService.onUnauthenticated(() => {
      logger.warn('User became unauthenticated, redirecting to login', undefined, {
        component: 'AuthProvider',
        action: 'unauthenticated',
      });

      // Redirect to login page
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    });
  }, [authService]);

  /**
   * Login with credentials
   */
  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      logger.info('Login attempt', undefined, {
        component: 'AuthProvider',
        action: 'login',
        username: credentials.username,
      });

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const token = await authService.login(credentials);

      setState({
        isAuthenticated: true,
        token,
        isLoading: false,
        error: null,
      });

      logger.info('Login successful', undefined, {
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
      logger.info('Logout attempt', undefined, {
        component: 'AuthProvider',
        action: 'logout',
      });

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      await authService.logout();

      setState({
        isAuthenticated: false,
        token: null,
        isLoading: false,
        error: null,
      });

      logger.info('Logout successful', undefined, {
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
      logger.info('Manual token refresh', undefined, {
        component: 'AuthProvider',
        action: 'refreshToken',
      });

      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const token = await authService.refreshToken();

      setState({
        isAuthenticated: true,
        token,
        isLoading: false,
        error: null,
      });

      logger.info('Token refresh successful', undefined, {
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
        token: null,
        isLoading: false,
        error: error as Error,
      });

      throw error;
    }
  };

  const contextValue: AuthContextState = {
    ...state,
    login,
    logout,
    refreshToken,
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
