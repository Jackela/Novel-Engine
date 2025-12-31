import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import config from '@/config/env';
import { logger } from '@/services/logging/LoggerFactory';
import type { IAuthenticationService } from '@/services/auth/IAuthenticationService';
import { TokenStorage } from '@/services/auth/TokenStorage';
import { JWTAuthService } from '@/services/auth/JWTAuthService';
import type { LoginRequest, AuthToken } from '@/types/auth';
import { createHttpClient } from '@/lib/api/httpClient';
import { guestAPI } from '@/services/api/guestAPI';

// Define missing types locally
export interface AuthProviderProps {
  children: ReactNode;
  authService?: IAuthenticationService;
}

export interface AuthInternalState {
  isAuthenticated: boolean;
  isGuest: boolean;
  token: AuthToken | null;
  workspaceId: string | null;
  isLoading: boolean;
  error: Error | null;
}

export interface AuthContextState extends AuthInternalState {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  enterGuestMode: () => Promise<void>;
}

const GUEST_SESSION_KEY = 'guest_session_active';

const createGuestToken = (): AuthToken => ({
  accessToken: 'guest_token',
  refreshToken: 'guest_refresh_token',
  tokenType: 'Bearer',
  expiresAt: Date.now() + 3600 * 1000,
  refreshExpiresAt: Date.now() + 7200 * 1000,
  user: {
    id: 'guest',
    username: 'Guest User',
    email: 'guest@example.com',
    roles: ['guest'],
  },
});

const AuthContext = createContext<AuthContextState | undefined>(undefined);

export const AuthProvider: React.FC<AuthProviderProps> = ({ children, authService: customAuthService }) => {
  const enableGuestMode = config.enableGuestMode;

  const [authService] = useState<IAuthenticationService>(() => {
    if (customAuthService) {
      return customAuthService;
    }

    const tokenStorage = new TokenStorage();
    const httpClient = createHttpClient({ baseURL: config.apiBaseUrl, timeout: config.apiTimeout });

    return new JWTAuthService(httpClient, tokenStorage);
  });

  const [state, setState] = useState<AuthInternalState>({
    isAuthenticated: false,
    isGuest: false,
    token: null,
    workspaceId: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const initializeAuth = async () => {
      let shouldResumeGuestSession = false;
      if (enableGuestMode && typeof window !== 'undefined') {
        try {
          shouldResumeGuestSession = window.localStorage.getItem(GUEST_SESSION_KEY) === '1';
        } catch (e) {
          logger.warn('Failed to read guest session from localStorage', e as Error, { component: 'AuthProvider' });
          shouldResumeGuestSession = false;
        }
      }

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
            // @ts-ignore - JWTAuthService might return a slightly different token shape or null, safe to cast or ignore for now if structure matches enough
            token: token as AuthToken | null,
            workspaceId: null,
            isLoading: false,
            error: null,
          });
        } else if (shouldResumeGuestSession) {
          try {
            const session = await guestAPI.createOrResumeSession();
            setState({
              isAuthenticated: true,
              isGuest: true,
              token: createGuestToken(),
              workspaceId: session.workspace_id,
              isLoading: false,
              error: null,
            });
          } catch (error) {
            logger.error('Failed to resume guest session', error as Error, {
              component: 'AuthProvider',
              action: 'initialize',
            });
            if (typeof window !== 'undefined') {
              try {
                window.sessionStorage.removeItem(GUEST_SESSION_KEY);
              } catch {
                // ignore storage errors
              }
            }
            setState({
              isAuthenticated: false,
              isGuest: false,
              token: null,
              workspaceId: null,
              isLoading: false,
              error: error as Error,
            });
          }
        } else {
          setState({
            isAuthenticated: false,
            isGuest: false,
            token: null,
            workspaceId: null,
            isLoading: false,
            error: null,
          });
        }

        if (isAuth) {
          authService.startTokenRefresh();
          logger.info('User authenticated, token refresh started', {
            component: 'AuthProvider',
            action: 'initialize',
            ...(token?.user?.id ? { userId: token.user.id } : {}),
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
          try {
            const session = await guestAPI.createOrResumeSession();
            setState({
              isAuthenticated: true,
              isGuest: true,
              token: createGuestToken(),
              workspaceId: session.workspace_id,
              isLoading: false,
              error: null,
            });
          } catch (guestError) {
            setState({
              isAuthenticated: false,
              isGuest: false,
              token: null,
              workspaceId: null,
              isLoading: false,
              error: guestError as Error,
            });
          }
        } else {
          setState({
            isAuthenticated: false,
            isGuest: false,
            token: null,
            workspaceId: null,
            isLoading: false,
            error: error as Error,
          });
        }
      }
    };

    initializeAuth();
  }, [authService, enableGuestMode]);

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
          // @ts-ignore
          token: authService.getToken() as AuthToken | null,
          workspaceId: null,
        }));
      } else if (enableGuestMode) {
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          isGuest: true,
          token: createGuestToken(),
          workspaceId: prev.workspaceId,
        }));
      } else {
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          isGuest: false,
          token: null,
          workspaceId: null,
        }));
      }
    });

    return () => {
      unsubscribe();
    };
  }, [authService, enableGuestMode]);

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
        // @ts-ignore
        token: token as AuthToken,
        workspaceId: null,
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
        workspaceId: null,
        isLoading: false,
        error: error as Error,
      });

      throw error;
    }
  };

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
            window.localStorage.removeItem(GUEST_SESSION_KEY);
          } catch (e) {
            logger.warn('Failed to remove guest session from localStorage during logout', e as Error, { component: 'AuthProvider' });
          }
        }
        setState(prev => ({
          ...prev,
          isAuthenticated: false,
          isGuest: false,
          token: null,
          workspaceId: null,
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
          workspaceId: null,
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
        // @ts-ignore
        token: token as AuthToken,
        workspaceId: null,
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
        workspaceId: null,
        isLoading: false,
        error: error as Error,
      });

      throw error;
    }
  };

  const enterGuestMode = async () => {
    if (!enableGuestMode) {
      logger.warn('Guest mode is disabled; ignoring enterGuestMode call');
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(GUEST_SESSION_KEY, '1');
      } catch (e) {
        logger.warn('Failed to set guest session in localStorage', e as Error, { component: 'AuthProvider' });
      }
    }

    try {
      const session = await guestAPI.createOrResumeSession();
      setState({
        isAuthenticated: true,
        isGuest: true,
        token: createGuestToken(),
        workspaceId: session.workspace_id,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      logger.error('Failed to create guest session', error as Error, { component: 'AuthProvider', action: 'enterGuestMode' });
      setState({
        isAuthenticated: false,
        isGuest: false,
        token: null,
        workspaceId: null,
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
    enterGuestMode,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = (): AuthContextState => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};
