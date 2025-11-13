/**
 * IAuthenticationService Interface
 * 
 * Port for authentication services (Hexagonal Architecture)
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Port interface for authentication
 * - Article IV (SSOT): Single source of truth for auth state
 * - Article V (SOLID): ISP - Interface Segregation Principle
 */

import type { LoginRequest, AuthToken } from '../../types/auth';

/**
 * Authentication state change callback
 */
export type AuthStateChangeCallback = (state: { isAuthenticated: boolean }) => void;

/**
 * Unauthenticated callback (for redirect to login)
 */
export type UnauthenticatedCallback = () => void;

/**
 * IAuthenticationService interface
 * 
 * Defines contract for authentication services (JWT, OAuth, etc.)
 */
export interface IAuthenticationService {
  /**
   * Login with credentials
   * @param credentials - Login credentials
   * @returns Promise with auth token
   */
  login(credentials: LoginRequest): Promise<AuthToken>;

  /**
   * Logout and clear authentication state
   * @returns Promise that resolves when logout is complete
   */
  logout(): Promise<void>;

  /**
   * Refresh access token using refresh token
   * @returns Promise with new auth token
   */
  refreshToken(): Promise<AuthToken>;

  /**
   * Check if user is authenticated
   * @returns Promise that resolves to true if authenticated
   */
  isAuthenticated(): Promise<boolean>;

  /**
   * Get current auth token
   * @returns Current token or null if not authenticated
   */
  getToken(): AuthToken | null;

  /**
   * Subscribe to auth state changes
   * @param callback - Function to call when auth state changes
   * @returns Unsubscribe function
   */
  onAuthStateChange(callback: AuthStateChangeCallback): () => void;

  /**
   * Register callback for when user becomes unauthenticated
   * @param callback - Function to call when user is no longer authenticated
   */
  onUnauthenticated(callback: UnauthenticatedCallback): void;

  /**
   * Start automatic token refresh mechanism
   * Refreshes token 5 minutes before expiration
   */
  startTokenRefresh(): void;

  /**
   * Stop automatic token refresh mechanism
   */
  stopTokenRefresh(): void;
}
