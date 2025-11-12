import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { authAPI } from '../../services/api/authAPI';

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

const initialState: AuthState = {
  user: null,
  accessToken: localStorage.getItem('accessToken'),
  refreshToken: localStorage.getItem('refreshToken'),
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
    
    // Store tokens in localStorage
    localStorage.setItem('accessToken', response.data.access_token);
    localStorage.setItem('refreshToken', response.data.refresh_token);
    
    return response;
  }
);

export const refreshUserToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { getState }) => {
    const state = getState() as { auth: AuthState };
    if (!state.auth.refreshToken) {
      throw new Error('No refresh token available');
    }
    
    const response = await authAPI.refreshToken({
      refresh_token: state.auth.refreshToken,
    });
    
    // Update stored tokens
    localStorage.setItem('accessToken', response.data.access_token);
    if (response.data.refresh_token) {
      localStorage.setItem('refreshToken', response.data.refresh_token);
    }
    
    return response;
  }
);

export const logoutUser = createAsyncThunk('auth/logoutUser', async () => {
  // Clear tokens from localStorage
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  
  // TODO: Call logout endpoint to invalidate tokens on server
  // await authAPI.logout();
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
      
      localStorage.setItem('accessToken', action.payload.accessToken);
      localStorage.setItem('refreshToken', action.payload.refreshToken);
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
        state.user = action.payload.data.user;
        state.accessToken = action.payload.data.access_token;
        state.refreshToken = action.payload.data.refresh_token;
        state.tokenExpiry = Date.now() + (action.payload.data.expires_in * 1000);
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
        state.accessToken = action.payload.data.access_token;
        if (action.payload.data.refresh_token) {
          state.refreshToken = action.payload.data.refresh_token;
        }
        state.tokenExpiry = Date.now() + (action.payload.data.expires_in * 1000);
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
