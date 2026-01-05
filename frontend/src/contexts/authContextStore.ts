import { createContext } from 'react';
import type { ReactNode } from 'react';
import type { IAuthenticationService } from '@/services/auth/IAuthenticationService';
import type { LoginRequest, AuthToken } from '@/types/auth';

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

export const GUEST_SESSION_KEY = 'guest_session_active';

export const createGuestToken = (): AuthToken => ({
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

export const AuthContext = createContext<AuthContextState | undefined>(undefined);
