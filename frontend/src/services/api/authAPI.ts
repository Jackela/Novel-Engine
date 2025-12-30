import { apiClient, handleAPIResponse, handleAPIError } from './apiClient';
import type { BaseAPIResponse } from './apiClient';
import type { User } from '@/store/slices/authSlice';

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
 * Token validation response from the server
 */
export interface TokenValidationData {
  valid: boolean;
  expires_at?: number; // milliseconds timestamp
  user_id?: string;
  error?: string;
}

/**
 * Authentication API service [SEC-001]
 *
 * Handles user login, token refresh, and logout operations using httpOnly cookies.
 *
 * Security improvements:
 * - Tokens stored in httpOnly cookies (XSS protection)
 * - CSRF protection via X-CSRF-Token header
 * - Automatic cookie sending via withCredentials
 * - No localStorage usage (mitigates XSS token theft)
 */
export class AuthAPI {
  /**
   * Authenticate user and obtain JWT token [SEC-001]
   *
   * This endpoint sets httpOnly cookies for access_token and refresh_token.
   * The response body also includes tokens for backward compatibility during migration.
   *
   * POST /api/auth/login
   *
   * @param credentials - User login credentials
   * @returns Authentication response with user data and tokens
   */
  async login(credentials: LoginRequest): Promise<BaseAPIResponse<AuthResponse>> {
    try {
      // Cookies are automatically sent with withCredentials: true
      const response = await apiClient.post('/api/auth/login', credentials);
      return handleAPIResponse(response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Refresh JWT token using refresh token [SEC-001]
   *
   * The refresh token is sent automatically via httpOnly cookie.
   * For backward compatibility, it can also be sent in the request body.
   *
   * POST /api/auth/refresh
   *
   * @param request - Refresh token request (optional during migration)
   * @returns New authentication tokens
   */
  async refreshToken(request: RefreshTokenRequest): Promise<BaseAPIResponse<AuthResponse>> {
    try {
      // Refresh token is automatically sent via httpOnly cookie
      // Request body is optional for backward compatibility
      const response = await apiClient.post('/api/auth/refresh', request);
      return handleAPIResponse(response);
    } catch (error) {
      return handleAPIError(error);
    }
  }

  /**
   * Logout user and invalidate session on the server [SEC-001]
   *
   * This endpoint clears httpOnly cookies on the server and logs the logout event.
   * The frontend no longer needs to clear localStorage as tokens are in httpOnly cookies.
   *
   * POST /api/auth/logout
   *
   * @returns Logout success response
   */
  async logout(): Promise<BaseAPIResponse<{ success: boolean; message: string }>> {
    try {
      // Server will clear httpOnly cookies
      const response = await apiClient.post('/api/auth/logout');
      return handleAPIResponse(response);
    } catch (error) {
      // Log the error but don't fail - logout should always succeed
      console.warn('Server logout call failed, but proceeding with logout:', error);

      // Return success anyway - httpOnly cookies can't be cleared by JS anyway
      // The important thing is the user experience
      return {
        success: true,
        data: {
          success: true,
          message: 'Logout completed (server notification failed)',
        },
        metadata: {
          timestamp: new Date().toISOString(),
          request_id: `req_${Date.now()}`,
        },
      };
    }
  }

  /**
   * Validate current token against the server
   * GET /api/auth/validate
   *
   * This checks if the stored token is still valid on the server.
   * Use this on app startup to verify a stored token before trusting it.
   *
   * @returns Response with validation status and expiry info
   */
  async validateToken(): Promise<BaseAPIResponse<{ valid: boolean; expires_at?: number; user_id?: string }>> {
    try {
      const response = await apiClient.get('/api/auth/validate');
      const data = response.data as TokenValidationData;

      const validationPayload: { valid: boolean; expires_at?: number; user_id?: string } = {
        valid: data.valid,
        ...(data.expires_at !== undefined ? { expires_at: data.expires_at } : {}),
        ...(data.user_id ? { user_id: data.user_id } : {}),
      };

      return {
        success: data.valid,
        data: validationPayload,
        metadata: {
          timestamp: new Date().toISOString(),
          request_id: `req_${Date.now()}`,
        },
      };
    } catch (error) {
      // A 401 response means the token is invalid - this is expected behavior
      const axiosError = error as { response?: { status?: number; data?: TokenValidationData } };
      if (axiosError.response?.status === 401) {
        const errorData = axiosError.response.data;
        return {
          success: false,
          data: { valid: false },
          error: {
            code: 'TOKEN_INVALID',
            message: errorData?.error || 'Token is invalid or expired',
            recoverable: true,
          },
          metadata: {
            timestamp: new Date().toISOString(),
            request_id: `req_${Date.now()}`,
          },
        };
      }

      // For other errors, return as invalid with error details
      console.error('Token validation failed with unexpected error:', error);
      return {
        success: false,
        data: {
          valid: false,
        },
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Failed to validate token',
          recoverable: true,
        },
        metadata: {
          timestamp: new Date().toISOString(),
          request_id: `req_${Date.now()}`,
        },
      };
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
