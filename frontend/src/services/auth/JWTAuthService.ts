/**
 * JWTAuthService Implementation
 * 
 * JWT-based authentication service with automatic token refresh
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Adapter implementing IAuthenticationService port
 * - Article IV (SSOT): Single source of truth for authentication state
 * - Article V (SOLID): SRP - Handles only authentication logic
 * - Article VII (Observability): Structured logging for auth events
 */

import type { AxiosInstance } from 'axios';
import { isAxiosError } from 'axios';
import type { LoginRequest, LoginResponse, AuthToken } from '@/types/auth';
import type { IAuthenticationService, AuthStateChangeCallback, UnauthenticatedCallback } from './IAuthenticationService';
import type { ITokenStorage } from './ITokenStorage';
import { logger } from '@/services/logging/LoggerFactory';

/**
 * JWTAuthService class
 * 
 * Implements JWT-based authentication with:
 * - Automatic token refresh (5 minutes before expiration)
 * - Auth state change notifications
 * - Secure token storage
 * - Error handling and recovery
 */
export class JWTAuthService implements IAuthenticationService {
  private httpClient: AxiosInstance;
  private tokenStorage: ITokenStorage;
  private refreshTimer: NodeJS.Timeout | null = null;
  private stateChangeCallbacks: AuthStateChangeCallback[] = [];
  private unauthenticatedCallbacks: UnauthenticatedCallback[] = [];
  private isRefreshing = false;
  private refreshPromise: Promise<AuthToken> | null = null;

  constructor(httpClient: AxiosInstance, tokenStorage: ITokenStorage) {
    this.httpClient = httpClient;
    this.tokenStorage = tokenStorage;
  }

  /**
   * Login with credentials
   * @param credentials - Login credentials
   * @returns Promise with auth token
   */
  async login(credentials: LoginRequest): Promise<AuthToken> {
    try {
      logger.info('Attempting login', undefined, {
        component: 'JWTAuthService',
        action: 'login',
        username: credentials.username,
      });

      const response = await this.httpClient.post<LoginResponse>('/auth/login', credentials);
      const loginResponse = response.data;

      // Convert LoginResponse to AuthToken
      const now = Date.now();
      const authToken: AuthToken = {
        accessToken: loginResponse.access_token,
        refreshToken: loginResponse.refresh_token,
        tokenType: loginResponse.token_type,
        expiresAt: now + loginResponse.expires_in * 1000,
        refreshExpiresAt: now + (loginResponse.refresh_expires_in || 7 * 24 * 60 * 60) * 1000,
        user: loginResponse.user,
      };

      // Save token to storage
      this.tokenStorage.saveToken(authToken);

      // Notify state change
      this.notifyStateChange(true);

      // Start automatic refresh
      this.startTokenRefresh();

      logger.info('Login successful', undefined, {
        component: 'JWTAuthService',
        action: 'login',
        userId: authToken.user.id,
        expiresAt: new Date(authToken.expiresAt).toISOString(),
      });

      return authToken;
    } catch (error) {
      const errorMessage = isAxiosError(error)
        ? error.response?.data?.message || 'Invalid credentials'
        : 'Invalid credentials';

      logger.error('Login failed', error as Error, {
        component: 'JWTAuthService',
        action: 'login',
        username: credentials.username,
        errorMessage,
      });

      throw new Error(errorMessage);
    }
  }

  /**
   * Logout and clear authentication state
   * @returns Promise that resolves when logout is complete
   */
  async logout(): Promise<void> {
    try {
      logger.info('Logging out', undefined, {
        component: 'JWTAuthService',
        action: 'logout',
      });

      // Stop automatic refresh
      this.stopTokenRefresh();

      // Call logout endpoint (fire-and-forget)
      try {
        await this.httpClient.post('/auth/logout');
      } catch (error) {
        // Ignore logout endpoint errors
        logger.warn('Logout endpoint failed, continuing with local logout', error as Error, {
          component: 'JWTAuthService',
          action: 'logout',
        });
      }

      // Clear token from storage
      this.tokenStorage.removeToken();

      // Notify state change
      this.notifyStateChange(false);

      logger.info('Logout successful', undefined, {
        component: 'JWTAuthService',
        action: 'logout',
      });
    } catch (error) {
      logger.error('Logout failed', error as Error, {
        component: 'JWTAuthService',
        action: 'logout',
      });
      throw error;
    }
  }

  /**
   * Refresh access token using refresh token
   * @returns Promise with new auth token
   */
  async refreshToken(): Promise<AuthToken> {
    // Prevent concurrent refresh requests
    if (this.isRefreshing && this.refreshPromise) {
      logger.debug('Token refresh already in progress, waiting', undefined, {
        component: 'JWTAuthService',
        action: 'refreshToken',
      });
      return this.refreshPromise;
    }

    this.isRefreshing = true;

    this.refreshPromise = (async () => {
      try {
        const currentToken = this.tokenStorage.getToken();
        if (!currentToken) {
          throw new Error('No refresh token available');
        }

        logger.info('Refreshing token', undefined, {
          component: 'JWTAuthService',
          action: 'refreshToken',
          userId: currentToken.user.id,
        });

        const response = await this.httpClient.post<LoginResponse>('/auth/refresh', {
          refresh_token: currentToken.refreshToken,
        });

        const refreshResponse = response.data;

        // Convert to AuthToken
        const now = Date.now();
        const newToken: AuthToken = {
          accessToken: refreshResponse.access_token,
          refreshToken: refreshResponse.refresh_token,
          tokenType: refreshResponse.token_type,
          expiresAt: now + refreshResponse.expires_in * 1000,
          refreshExpiresAt: now + (refreshResponse.refresh_expires_in || 7 * 24 * 60 * 60) * 1000,
          user: refreshResponse.user,
        };

        // Save new token
        this.tokenStorage.saveToken(newToken);

        logger.info('Token refresh successful', undefined, {
          component: 'JWTAuthService',
          action: 'refreshToken',
          userId: newToken.user.id,
          expiresAt: new Date(newToken.expiresAt).toISOString(),
        });

        return newToken;
      } catch (error) {
        const errorMessage = isAxiosError(error)
          ? error.response?.data?.message || 'Token refresh failed'
          : 'Token refresh failed';

        logger.error('Token refresh failed', error as Error, {
          component: 'JWTAuthService',
          action: 'refreshToken',
          errorMessage,
        });

        // Clear invalid token
        this.tokenStorage.removeToken();
        this.notifyStateChange(false);
        this.notifyUnauthenticated();

        throw new Error(errorMessage);
      } finally {
        this.isRefreshing = false;
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  /**
   * Check if user is authenticated
   * @returns Promise that resolves to true if authenticated
   */
  async isAuthenticated(): Promise<boolean> {
    const token = this.tokenStorage.getToken();

    if (!token) {
      return false;
    }

    // Check if token is expired
    const now = Date.now();
    if (token.expiresAt < now) {
      logger.debug('Token expired', undefined, {
        component: 'JWTAuthService',
        action: 'isAuthenticated',
        expiresAt: new Date(token.expiresAt).toISOString(),
      });
      this.tokenStorage.removeToken();
      return false;
    }

    return true;
  }

  /**
   * Get current auth token
   * @returns Current token or null if not authenticated
   */
  getToken(): AuthToken | null {
    return this.tokenStorage.getToken();
  }

  /**
   * Subscribe to auth state changes
   * @param callback - Function to call when auth state changes
   * @returns Unsubscribe function
   */
  onAuthStateChange(callback: AuthStateChangeCallback): () => void {
    this.stateChangeCallbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.stateChangeCallbacks.indexOf(callback);
      if (index > -1) {
        this.stateChangeCallbacks.splice(index, 1);
      }
    };
  }

  /**
   * Register callback for when user becomes unauthenticated
   * @param callback - Function to call when user is no longer authenticated
   */
  onUnauthenticated(callback: UnauthenticatedCallback): void {
    this.unauthenticatedCallbacks.push(callback);
  }

  /**
   * Start automatic token refresh with intelligent scheduling
   * 
   * Token Refresh Strategy:
   * 1. If token expires in <5 minutes: Refresh immediately
   * 2. Otherwise: Schedule refresh for (expiration - 5 minutes)
   * 3. After successful refresh: Recursively schedule next refresh
   * 4. On failure: Log error, trigger unauthenticated notification
   * 
   * This prevents session interruption and handles edge cases like:
   * - Token already expired when page loads
   * - Token expiring during user activity
   * - Network failures during refresh
   */
  startTokenRefresh(): void {
    // Clear existing timer to prevent duplicate refresh attempts
    this.stopTokenRefresh();

    const scheduleRefresh = () => {
      const token = this.tokenStorage.getToken();

      if (!token) {
        logger.debug('No token to refresh', undefined, {
          component: 'JWTAuthService',
          action: 'startTokenRefresh',
        });
        return;
      }

      const now = Date.now();
      const timeUntilExpiry = token.expiresAt - now;
      const refreshThreshold = 5 * 60 * 1000; // 5 minutes

      // If token expires in less than 5 minutes, refresh now
      if (timeUntilExpiry <= refreshThreshold) {
        logger.info('Token expiring soon, refreshing now', undefined, {
          component: 'JWTAuthService',
          action: 'startTokenRefresh',
          timeUntilExpiry: Math.floor(timeUntilExpiry / 1000),
        });

        this.refreshToken()
          .then(() => {
            // Schedule next refresh after successful refresh
            scheduleRefresh();
          })
          .catch((error) => {
            logger.error('Automatic token refresh failed', error, {
              component: 'JWTAuthService',
              action: 'startTokenRefresh',
            });
          });
      } else {
        // Schedule refresh for 5 minutes before expiry
        const delay = timeUntilExpiry - refreshThreshold;

        logger.debug('Scheduling token refresh', undefined, {
          component: 'JWTAuthService',
          action: 'startTokenRefresh',
          delaySeconds: Math.floor(delay / 1000),
          refreshAt: new Date(now + delay).toISOString(),
        });

        this.refreshTimer = setTimeout(() => {
          this.refreshToken()
            .then(() => {
              // Schedule next refresh after successful refresh
              scheduleRefresh();
            })
            .catch((error) => {
              logger.error('Automatic token refresh failed', error, {
                component: 'JWTAuthService',
                action: 'startTokenRefresh',
              });
            });
        }, delay);
      }
    };

    scheduleRefresh();
  }

  /**
   * Stop automatic token refresh mechanism
   */
  stopTokenRefresh(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;

      logger.debug('Token refresh stopped', undefined, {
        component: 'JWTAuthService',
        action: 'stopTokenRefresh',
      });
    }
  }

  /**
   * Notify all subscribers of auth state change
   * @param isAuthenticated - New authentication state
   */
  private notifyStateChange(isAuthenticated: boolean): void {
    this.stateChangeCallbacks.forEach(callback => {
      try {
        callback({ isAuthenticated });
      } catch (error) {
        logger.error('Auth state change callback failed', error as Error, {
          component: 'JWTAuthService',
          action: 'notifyStateChange',
        });
      }
    });
  }

  /**
   * Notify all unauthenticated callbacks
   */
  private notifyUnauthenticated(): void {
    this.unauthenticatedCallbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        logger.error('Unauthenticated callback failed', error as Error, {
          component: 'JWTAuthService',
          action: 'notifyUnauthenticated',
        });
      }
    });
  }
}
