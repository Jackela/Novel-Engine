import { apiClient, handleAPIResponse, handleAPIError, BaseAPIResponse } from './apiClient';
import { User } from '../../store/slices/authSlice';

// Authentication request/response types based on OpenAPI spec
export interface LoginRequest {
  email: string;
  password: string;
  provider?: 'email' | 'google' | 'github' | 'discord';
  oauth_token?: string;
  remember_me?: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: 'Bearer';
  user: User;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

/**
 * Authentication API service
 * Handles user login, token refresh, and logout operations
 */
export class AuthAPI {
  /**
   * Authenticate user and obtain JWT token
   * POST /auth/login
   */
  async login(credentials: LoginRequest): Promise<BaseAPIResponse<AuthResponse>> {
    try {
      const response = await apiClient.post('/auth/login', credentials);
      return handleAPIResponse(response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Refresh JWT token using refresh token
   * POST /auth/refresh
   */
  async refreshToken(request: RefreshTokenRequest): Promise<BaseAPIResponse<AuthResponse>> {
    try {
      const response = await apiClient.post('/auth/refresh', request);
      return handleAPIResponse(response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Logout user (future implementation)
   * This would invalidate tokens on the server side
   */
  async logout(): Promise<BaseAPIResponse<void>> {
    try {
      // TODO: Implement logout endpoint when available
      // const response = await apiClient.post('/auth/logout');
      // return handleAPIResponse(response);
      
      // For now, just return success
      return {
        success: true,
        metadata: {
          timestamp: new Date().toISOString(),
          request_id: `req_${Date.now()}`,
        },
      };
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Validate current token (future implementation)
   * This would check if the current token is still valid
   */
  async validateToken(): Promise<BaseAPIResponse<{ valid: boolean; user: User }>> {
    try {
      // TODO: Implement token validation endpoint when available
      // const response = await apiClient.get('/auth/validate');
      // return handleAPIResponse(response);
      
      // For now, assume token is valid if we have one
      throw new Error('Token validation not yet implemented');
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Get current user profile
   * This could be used to refresh user data
   */
  async getCurrentUser(): Promise<BaseAPIResponse<User>> {
    try {
      // TODO: Implement get current user endpoint when available
      // const response = await apiClient.get('/auth/me');
      // return handleAPIResponse(response);
      
      throw new Error('Get current user not yet implemented');
    } catch (error) {
      return handleAPIError(error);
    }
  }
}

// Export singleton instance
export const authAPI = new AuthAPI();