import React, { useState, useEffect, useCallback } from 'react';
import config from '@/config/env';
import { logger } from '@/services/logging/LoggerFactory';
import type { IAuthenticationService } from '@/services/auth/IAuthenticationService';
import { TokenStorage } from '@/services/auth/TokenStorage';
import { JWTAuthService } from '@/services/auth/JWTAuthService';
import type { LoginRequest, AuthToken } from '@/types/auth';
import { createHttpClient } from '@/lib/api/httpClient';
import { guestAPI } from '@/services/api/guestAPI';
import {
  AuthContext,
  createGuestToken,
  GUEST_SESSION_KEY,
} from './authContextStore';
import type {
  AuthProviderProps,
  AuthInternalState,
  AuthContextState,
} from './authContextStore';

const buildAuthService = (customAuthService?: IAuthenticationService): IAuthenticationService => {
  if (customAuthService) {
    return customAuthService;
  }
  const tokenStorage = new TokenStorage();
  const httpClient = createHttpClient({ baseURL: config.apiBaseUrl, timeout: config.apiTimeout });
  return new JWTAuthService(httpClient, tokenStorage);
};

const buildAuthState = (params: {
  isAuthenticated: boolean;
  isGuest: boolean;
  token: AuthToken | null;
  workspaceId: string | null;
  isLoading?: boolean;
  error?: Error | null;
}): AuthInternalState => ({
  isAuthenticated: params.isAuthenticated,
  isGuest: params.isGuest,
  token: params.token,
  workspaceId: params.workspaceId,
  isLoading: params.isLoading ?? false,
  error: params.error ?? null,
});

const buildAuthenticatedState = (token: AuthToken | null): AuthInternalState =>
  buildAuthState({
    isAuthenticated: true,
    isGuest: false,
    token,
    workspaceId: null,
  });

const buildGuestState = (workspaceId: string | null): AuthInternalState =>
  buildAuthState({
    isAuthenticated: true,
    isGuest: true,
    token: createGuestToken(),
    workspaceId,
  });

const buildSignedOutState = (error: Error | null = null): AuthInternalState =>
  buildAuthState({
    isAuthenticated: false,
    isGuest: false,
    token: null,
    workspaceId: null,
    error,
  });

const loadGuestState = async (): Promise<AuthInternalState> => {
  const session = await guestAPI.createOrResumeSession();
  return buildGuestState(session.workspace_id);
};

const setLoadingState = (setState: React.Dispatch<React.SetStateAction<AuthInternalState>>) => {
  setState(prev => ({ ...prev, isLoading: true, error: null }));
};

const setAuthState = (
  setState: React.Dispatch<React.SetStateAction<AuthInternalState>>,
  next: AuthInternalState
) => {
  setState(next);
};

const clearGuestSessionFlag = () => {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(GUEST_SESSION_KEY);
  } catch {
    // ignore storage errors
  }
};

const setGuestSessionFlag = () => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(GUEST_SESSION_KEY, '1');
  } catch (error) {
    logger.warn('Failed to set guest session in localStorage', error as Error, { component: 'AuthProvider' });
  }
};

const shouldResumeGuest = (enableGuestMode: boolean): boolean => {
  if (!enableGuestMode || typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(GUEST_SESSION_KEY) === '1';
  } catch (error) {
    logger.warn('Failed to read guest session from localStorage', error as Error, { component: 'AuthProvider' });
    return false;
  }
};

const useAuthInitialization = (
  authService: IAuthenticationService,
  enableGuestMode: boolean,
  setState: React.Dispatch<React.SetStateAction<AuthInternalState>>
) => {
  useEffect(() => {
    const initializeAuth = async () => {
      const shouldResumeGuestSession = shouldResumeGuest(enableGuestMode);

      try {
        logger.info('Initializing authentication state', {
          component: 'AuthProvider',
          action: 'initialize',
        });

        const isAuth = await authService.isAuthenticated();
        const token = authService.getToken();

        if (isAuth) {
          setAuthState(setState, buildAuthenticatedState(token as AuthToken | null));
        } else if (shouldResumeGuestSession) {
          const guestState = await loadGuestState();
          setAuthState(setState, guestState);
        } else {
          setAuthState(setState, buildSignedOutState());
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
            const guestState = await loadGuestState();
            setAuthState(setState, guestState);
          } catch (guestError) {
            setAuthState(setState, buildSignedOutState(guestError as Error));
          }
        } else {
          setAuthState(setState, buildSignedOutState(error as Error));
        }
      }
    };

    initializeAuth();
  }, [authService, enableGuestMode, setState]);
};

const useAuthStateSubscription = (
  authService: IAuthenticationService,
  enableGuestMode: boolean,
  setState: React.Dispatch<React.SetStateAction<AuthInternalState>>
) => {
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
  }, [authService, enableGuestMode, setState]);
};

const useUnauthenticatedRedirect = (
  authService: IAuthenticationService,
  enableGuestMode: boolean
) => {
  useEffect(() => {
    if (enableGuestMode) return;
    authService.onUnauthenticated(() => {
      logger.warn('User became unauthenticated, redirecting to login', {
        component: 'AuthProvider',
        action: 'unauthenticated',
      });

      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    });
  }, [authService, enableGuestMode]);
};

const useLoginAction = (
  authService: IAuthenticationService,
  setState: React.Dispatch<React.SetStateAction<AuthInternalState>>
) =>
  useCallback(
    async (credentials: LoginRequest): Promise<void> => {
      try {
        logger.info('Login attempt', {
          component: 'AuthProvider',
          action: 'login',
          username: credentials.username,
        });

        setLoadingState(setState);
        const token = await authService.login(credentials);
        setAuthState(setState, buildAuthenticatedState(token as AuthToken));

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

        setAuthState(setState, buildSignedOutState(error as Error));
        throw error;
      }
    },
    [authService, setState]
  );

const useLogoutAction = (
  authService: IAuthenticationService,
  enableGuestMode: boolean,
  state: AuthInternalState,
  setState: React.Dispatch<React.SetStateAction<AuthInternalState>>
) =>
  useCallback(async (): Promise<void> => {
    try {
      logger.info('Logout attempt', {
        component: 'AuthProvider',
        action: 'logout',
      });

      setLoadingState(setState);

      if (state.isGuest && enableGuestMode) {
        if (typeof window !== 'undefined') {
          try {
            window.localStorage.removeItem(GUEST_SESSION_KEY);
          } catch (error) {
            logger.warn('Failed to remove guest session from localStorage during logout', error as Error, { component: 'AuthProvider' });
          }
        }
        setAuthState(setState, buildSignedOutState());
        if (typeof window !== 'undefined') {
          window.location.href = '/';
        }
        return;
      }

      await authService.logout();
      setAuthState(setState, buildSignedOutState());

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
  }, [authService, enableGuestMode, setState, state.isGuest]);

const useRefreshTokenAction = (
  authService: IAuthenticationService,
  setState: React.Dispatch<React.SetStateAction<AuthInternalState>>
) =>
  useCallback(async (): Promise<void> => {
    try {
      logger.info('Manual token refresh', {
        component: 'AuthProvider',
        action: 'refreshToken',
      });

      setLoadingState(setState);
      const token = await authService.refreshToken();

      setAuthState(setState, buildAuthenticatedState(token as AuthToken));

      logger.info('Token refresh successful', {
        component: 'AuthProvider',
        action: 'refreshToken',
      });
    } catch (error) {
      logger.error('Token refresh failed', error as Error, {
        component: 'AuthProvider',
        action: 'refreshToken',
      });

      setAuthState(setState, buildSignedOutState(error as Error));

      throw error;
    }
  }, [authService, setState]);

const useEnterGuestModeAction = (
  enableGuestMode: boolean,
  setState: React.Dispatch<React.SetStateAction<AuthInternalState>>
) =>
  useCallback(async () => {
    if (!enableGuestMode) {
      logger.warn('Guest mode is disabled; ignoring enterGuestMode call');
      return;
    }

    setLoadingState(setState);
    setGuestSessionFlag();

    try {
      const guestState = await loadGuestState();
      setAuthState(setState, guestState);
    } catch (error) {
      logger.error('Failed to create guest session', error as Error, { component: 'AuthProvider', action: 'enterGuestMode' });
      setAuthState(setState, buildSignedOutState(error as Error));
      throw error;
    }
  }, [enableGuestMode, setState]);

export const AuthProvider: React.FC<AuthProviderProps> = ({ children, authService: customAuthService }) => {
  const enableGuestMode = config.enableGuestMode;

  const [authService] = useState<IAuthenticationService>(() => buildAuthService(customAuthService));

  const [state, setState] = useState<AuthInternalState>({
    isAuthenticated: false,
    isGuest: false,
    token: null,
    workspaceId: null,
    isLoading: true,
    error: null,
  });

  useAuthInitialization(authService, enableGuestMode, setState);
  useAuthStateSubscription(authService, enableGuestMode, setState);
  useUnauthenticatedRedirect(authService, enableGuestMode);

  const login = useLoginAction(authService, setState);
  const logout = useLogoutAction(authService, enableGuestMode, state, setState);
  const refreshToken = useRefreshTokenAction(authService, setState);
  const enterGuestMode = useEnterGuestModeAction(enableGuestMode, setState);

  const contextValue: AuthContextState = {
    ...state,
    login,
    logout,
    refreshToken,
    enterGuestMode,
  };

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};
