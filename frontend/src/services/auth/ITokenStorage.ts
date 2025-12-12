/**
 * ITokenStorage Interface
 * 
 * Port for token storage mechanisms (Hexagonal Architecture)
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Port interface for storage
 * - Article IV (SSOT): Single source of truth for token persistence
 * - Article V (SOLID): ISP - Interface Segregation Principle
 */

import type { AuthToken } from '@/types/auth';

/**
 * ITokenStorage interface
 * 
 * Defines contract for token storage implementations
 * (httpOnly cookies, sessionStorage, localStorage, etc.)
 */
export interface ITokenStorage {
  /**
   * Save authentication token
   * @param token - Auth token to save
   */
  saveToken(token: AuthToken): void;

  /**
   * Get saved authentication token
   * @returns Saved token or null if not found
   */
  getToken(): AuthToken | null;

  /**
   * Remove authentication token
   */
  removeToken(): void;

  /**
   * Check if token exists
   * @returns True if token exists in storage
   */
  hasToken(): boolean;
}
