/**
 * JWTAuthService Unit Tests (TDD Green Phase)
 * 
 * Tests for JWT-based authentication service with automatic token refresh
 * 
 * Constitution Compliance:
 * - Article III (TDD): Write failing tests BEFORE implementation
 * - Article V (SOLID): Test against IAuthenticationService interface
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { LoginRequest, LoginResponse, AuthToken } from '../../../src/types/auth';
import { JWTAuthService } from '../../../src/services/auth/JWTAuthService';

// Mock axios for API calls
vi.mock('axios');
const mockAxios = {
  post: vi.fn(),
};

// Mock ITokenStorage
const mockTokenStorage = {
  saveToken: vi.fn(),
  getToken: vi.fn(),
  removeToken: vi.fn(),
};

describe('JWTAuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('T037 - Login with valid credentials', () => {
    it('should login successfully with valid credentials', async () => {
      // Arrange
      const loginRequest: LoginRequest = {
        username: 'testuser',
        password: 'testpassword123',
      };

      const mockLoginResponse: LoginResponse = {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600, // 1 hour
        refresh_expires_in: 604800, // 7 days
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockAxios.post.mockResolvedValue({ data: mockLoginResponse });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      const authToken = await authService.login(loginRequest);

      // Assert
      expect(mockAxios.post).toHaveBeenCalledWith('/auth/login', loginRequest);
      expect(authToken.accessToken).toBe('mock-access-token');
      expect(authToken.refreshToken).toBe('mock-refresh-token');
      expect(authToken.user.username).toBe('testuser');
      expect(mockTokenStorage.saveToken).toHaveBeenCalledWith(authToken);
      
    });

    it('should throw error on login failure with invalid credentials', async () => {
      // Arrange
      const loginRequest: LoginRequest = {
        username: 'testuser',
        password: 'wrongpassword',
      };

      mockAxios.post.mockRejectedValue({
        response: {
          status: 401,
          data: { message: 'Invalid credentials' },
        },
      });

      // Act & Assert
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      await expect(authService.login(loginRequest)).rejects.toThrow('Invalid credentials');
      
    });

    it('should calculate correct expiresAt timestamp based on expires_in', async () => {
      // Arrange
      const now = Date.now();
      vi.setSystemTime(now);

      const mockLoginResponse: LoginResponse = {
        access_token: 'mock-token',
        refresh_token: 'mock-refresh',
        token_type: 'Bearer',
        expires_in: 3600, // 1 hour
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockAxios.post.mockResolvedValue({ data: mockLoginResponse });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      const authToken = await authService.login({ username: 'test', password: 'test' });

      // Assert
      expect(authToken.expiresAt).toBe(now + 3600 * 1000);
      
    });
  });

  describe('T038 - Token refresh before expiration', () => {
    it('should refresh token automatically 5 minutes before expiration', async () => {
      // Arrange
      const now = Date.now();
      vi.setSystemTime(now);

      const existingToken: AuthToken = {
        accessToken: 'old-token',
        refreshToken: 'refresh-token',
        tokenType: 'Bearer',
        expiresAt: now + 4 * 60 * 1000, // Expires in 4 minutes (within 5-min threshold)
        refreshExpiresAt: now + 7 * 24 * 60 * 60 * 1000, // 7 days
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      const mockRefreshResponse: LoginResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: existingToken.user,
      };

      mockTokenStorage.getToken.mockReturnValue(existingToken);
      mockAxios.post.mockResolvedValue({ data: mockRefreshResponse });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      authService.startTokenRefresh(); // Start automatic refresh (synchronous)

      // Wait for microtasks to resolve (the immediate refresh promise)
      await Promise.resolve();
      await Promise.resolve();

      // Assert
      expect(mockAxios.post).toHaveBeenCalledWith('/auth/refresh', {
        refresh_token: 'refresh-token',
      });
      expect(mockTokenStorage.saveToken).toHaveBeenCalled();
      
    });

    it('should NOT refresh token if more than 5 minutes until expiration', async () => {
      // Arrange
      const now = Date.now();
      vi.setSystemTime(now);

      const existingToken: AuthToken = {
        accessToken: 'token',
        refreshToken: 'refresh-token',
        tokenType: 'Bearer',
        expiresAt: now + 20 * 60 * 1000, // Expires in 20 minutes
        refreshExpiresAt: now + 7 * 24 * 60 * 60 * 1000,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockTokenStorage.getToken.mockReturnValue(existingToken);
      vi.clearAllMocks(); // Clear any previous mock calls

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      authService.startTokenRefresh();

      // Advance time by 1 minute
      vi.advanceTimersByTime(1 * 60 * 1000);
      await Promise.resolve(); // Wait for any microtasks

      // Assert - should NOT have called refresh
      expect(mockAxios.post).not.toHaveBeenCalled();
      
    });

    it('should handle refresh token failure and clear auth state', async () => {
      // Arrange
      const now = Date.now();
      const existingToken: AuthToken = {
        accessToken: 'token',
        refreshToken: 'invalid-refresh',
        tokenType: 'Bearer',
        expiresAt: now + 4 * 60 * 1000, // Expires in 4 minutes
        refreshExpiresAt: now + 7 * 24 * 60 * 60 * 1000,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockTokenStorage.getToken.mockReturnValue(existingToken);
      mockAxios.post.mockRejectedValue({
        response: { status: 401, data: { message: 'Invalid refresh token' } },
      });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      await authService.startTokenRefresh();
      vi.advanceTimersByTime(1 * 60 * 1000);

      // Assert
      expect(mockTokenStorage.removeToken).toHaveBeenCalled();
      
    });
  });

  describe('T039 - Logout clearing tokens', () => {
    it('should clear tokens on logout', async () => {
      // Arrange
      const existingToken: AuthToken = {
        accessToken: 'token',
        refreshToken: 'refresh',
        tokenType: 'Bearer',
        expiresAt: Date.now() + 3600 * 1000,
        refreshExpiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockTokenStorage.getToken.mockReturnValue(existingToken);
      mockAxios.post.mockResolvedValue({ data: { success: true } });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      
      // After logout, token should be removed
      mockTokenStorage.getToken.mockReturnValue(null);
      await authService.logout();

      // Assert
      expect(mockTokenStorage.removeToken).toHaveBeenCalled();
      expect(await authService.isAuthenticated()).toBe(false);
      
    });

    it('should stop automatic token refresh on logout', async () => {
      // Arrange
      const existingToken: AuthToken = {
        accessToken: 'token',
        refreshToken: 'refresh',
        tokenType: 'Bearer',
        expiresAt: Date.now() + 6 * 60 * 1000,
        refreshExpiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockTokenStorage.getToken.mockReturnValue(existingToken);
      mockAxios.post.mockResolvedValue({ data: { success: true } });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      await authService.startTokenRefresh();
      
      // Clear mocks before logout to verify no refresh calls after
      vi.clearAllMocks();
      
      await authService.logout();

      // Advance time - should NOT trigger refresh after logout
      vi.advanceTimersByTime(2 * 60 * 1000);

      // Assert - should only see the logout call, not any refresh calls
      const refreshCalls = mockAxios.post.mock.calls.filter(
        call => call[0] === '/auth/refresh'
      );
      expect(refreshCalls).toHaveLength(0);
      
    });

    it('should call logout endpoint on server', async () => {
      // Arrange
      mockAxios.post.mockResolvedValue({ data: { success: true } });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      await authService.logout();

      // Assert
      expect(mockAxios.post).toHaveBeenCalledWith('/auth/logout');
      
    });
  });

  describe('T040 - Auth state change notifications', () => {
    it('should notify subscribers when auth state changes on login', async () => {
      // Arrange
      const mockCallback = vi.fn();
      const mockLoginResponse: LoginResponse = {
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockAxios.post.mockResolvedValue({ data: mockLoginResponse });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      authService.onAuthStateChange(mockCallback);
      await authService.login({ username: 'test', password: 'test' });

      // Assert
      expect(mockCallback).toHaveBeenCalledWith({ isAuthenticated: true });
      
    });

    it('should notify subscribers when auth state changes on logout', async () => {
      // Arrange
      const mockCallback = vi.fn();

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      authService.onAuthStateChange(mockCallback);
      await authService.logout();

      // Assert
      expect(mockCallback).toHaveBeenCalledWith({ isAuthenticated: false });
      
    });

    it('should allow multiple subscribers', async () => {
      // Arrange
      const callback1 = vi.fn();
      const callback2 = vi.fn();
      const callback3 = vi.fn();

      const mockLoginResponse: LoginResponse = {
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'Bearer',
        expires_in: 3600,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockAxios.post.mockResolvedValue({ data: mockLoginResponse });

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      authService.onAuthStateChange(callback1);
      authService.onAuthStateChange(callback2);
      authService.onAuthStateChange(callback3);
      await authService.login({ username: 'test', password: 'test' });

      // Assert
      expect(callback1).toHaveBeenCalled();
      expect(callback2).toHaveBeenCalled();
      expect(callback3).toHaveBeenCalled();
      
    });

    it('should allow unsubscribing from auth state changes', async () => {
      // Arrange
      const mockCallback = vi.fn();

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      const unsubscribe = authService.onAuthStateChange(mockCallback);
      unsubscribe(); // Unsubscribe
      await authService.logout();

      // Assert
      expect(mockCallback).not.toHaveBeenCalled();
      
    });
  });

  describe('isAuthenticated', () => {
    it('should return true when valid token exists', async () => {
      // Arrange
      const validToken: AuthToken = {
        accessToken: 'token',
        refreshToken: 'refresh',
        tokenType: 'Bearer',
        expiresAt: Date.now() + 3600 * 1000, // Not expired
        refreshExpiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockTokenStorage.getToken.mockReturnValue(validToken);

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      const isAuth = await authService.isAuthenticated();

      // Assert
      expect(isAuth).toBe(true);
      
    });

    it('should return false when token is expired', async () => {
      // Arrange
      const expiredToken: AuthToken = {
        accessToken: 'token',
        refreshToken: 'refresh',
        tokenType: 'Bearer',
        expiresAt: Date.now() - 1000, // Expired 1 second ago
        refreshExpiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000,
        user: {
          id: 'user-123',
          username: 'testuser',
          email: 'test@example.com',
          roles: ['user'],
        },
      };

      mockTokenStorage.getToken.mockReturnValue(expiredToken);

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      const isAuth = await authService.isAuthenticated();

      // Assert
      expect(isAuth).toBe(false);
      
    });

    it('should return false when no token exists', async () => {
      // Arrange
      mockTokenStorage.getToken.mockReturnValue(null);

      // Act
      const authService = new JWTAuthService(mockAxios, mockTokenStorage);
      const isAuth = await authService.isAuthenticated();

      // Assert
      expect(isAuth).toBe(false);
      
    });
  });
});
