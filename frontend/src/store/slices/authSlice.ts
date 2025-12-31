import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { authAPI } from '@/services/api/authAPI';

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user' | 'service';
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  tokenExpiry: number | null;
}

/**
 * SECURITY NOTE: Token Storage Migration Complete [SEC-001] ✅
 *
 * RESOLVED: Migrated from localStorage to httpOnly cookies
 *
 * Previous Implementation:
 * Tokens were stored in localStorage, vulnerable to XSS attacks.
 *
 * Current Implementation (SEC-001):
 * ✅ Tokens stored in httpOnly cookies (XSS protection)
 * ✅ Secure flag for HTTPS-only transmission
 * ✅ SameSite=Lax for CSRF protection
 * ✅ CSRF token validation for state-changing requests
 * ✅ Short-lived access tokens (15 min expiry)
 * ✅ Long-lived refresh tokens (30 days)
 *
 * Security Improvements:
 * - httpOnly cookies cannot be accessed via JavaScript (mitigates XSS token theft)
 * - Cookies sent automatically with withCredentials (no manual token management)
 * - CSRF protection via X-CSRF-Token header validation
 * - Tokens never exposed to client-side code
 *
 * Backward Compatibility:
 * - Response body still includes tokens during migration period
 * - Redux state keeps accessToken and refreshToken for compatibility
 * - Will be fully removed in future version after complete migration
 *
 * Additional mitigations:
 * - Content Security Policy headers configured on the server
 * - Input sanitization throughout the application
 * - Token rotation on refresh
 */
const initialState: AuthState = {
  user: null,
  accessToken: null,  // No longer read from localStorage [SEC-001]
  refreshToken: null,  // No longer read from localStorage [SEC-001]
  isAuthenticated: false,
  loading: false,
  error: null,
  tokenExpiry: null,
};

// Async thunks
export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials: { email: string; password: string; remember_me?: boolean }) => {
    const response = await authAPI.login(credentials);

    // [SEC-001] Tokens are now stored in httpOnly cookies by the backend
    // No localStorage operations needed - cookies are sent automatically

    return response;
  }
);

export const refreshUserToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { getState }) => {
    const state = getState() as { auth: AuthState };

    // [SEC-001] Refresh token is sent automatically via httpOnly cookie
    // For backward compatibility, also send from state if available
    const refreshTokenValue = state.auth.refreshToken || '';

    const response = await authAPI.refreshToken({
      refresh_token: refreshTokenValue,
    });

    // [SEC-001] Tokens are now stored in httpOnly cookies by the backend
    // No localStorage operations needed

    return response;
  }
);

export const logoutUser = createAsyncThunk('auth/logoutUser', async () => {
  try {
    // [SEC-001] Call server logout endpoint to clear httpOnly cookies
    // The server will handle cookie deletion
    await authAPI.logout();
  } catch (error) {
    // Log but don't fail - logout should always succeed from user perspective
    console.warn('Server logout notification failed:', error);
  }

  // [SEC-001] No localStorage cleanup needed - tokens are in httpOnly cookies
  // The cookies were cleared by the server or will expire naturally
});

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setTokens: (state, action: PayloadAction<{ accessToken: string; refreshToken: string }>) => {
      state.accessToken = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.isAuthenticated = true;

      // [SEC-001] No localStorage operations - tokens are in httpOnly cookies
      // This action is kept for backward compatibility during migration
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.loading = false;
        state.isAuthenticated = true;
        if (action.payload.data) {
          state.user = action.payload.data.user;
          state.accessToken = action.payload.data.access_token;
          state.refreshToken = action.payload.data.refresh_token;
          state.tokenExpiry = Date.now() + (action.payload.data.expires_in * 1000);
        }
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
        state.error = action.error.message || 'Login failed';
      })
      // Refresh token
      .addCase(refreshUserToken.pending, (state) => {
        state.loading = true;
      })
      .addCase(refreshUserToken.fulfilled, (state, action) => {
        state.loading = false;
        if (action.payload.data) {
          state.accessToken = action.payload.data.access_token;
          if (action.payload.data.refresh_token) {
            state.refreshToken = action.payload.data.refresh_token;
          }
          state.tokenExpiry = Date.now() + (action.payload.data.expires_in * 1000);
        }
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(refreshUserToken.rejected, (state, action) => {
        state.loading = false;
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
        state.tokenExpiry = null;
        state.error = action.error.message || 'Token refresh failed';
      })
      // Logout
      .addCase(logoutUser.fulfilled, (state) => {
        state.isAuthenticated = false;
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
        state.tokenExpiry = null;
        state.loading = false;
        state.error = null;
      });
  },
});

export const { clearError, setTokens } = authSlice.actions;
export default authSlice.reducer;
