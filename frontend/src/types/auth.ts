export interface AuthToken {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresAt: number;
  refreshExpiresAt: number;
  user: {
    id: string;
    username: string;
    email: string;
    roles: string[];
  };
}

export interface AuthState {
  isAuthenticated: boolean;
  token: AuthToken | null;
  isRefreshing: boolean;
  lastError: Error | null;
  lastLoginAt: string | null;
  isInitialized: boolean;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in?: number;
  user: {
    id: string;
    username: string;
    email: string;
    roles: string[];
  };
}
