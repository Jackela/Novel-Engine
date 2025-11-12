/**
 * TokenStorage Implementation
 * 
 * Adapter for token storage using sessionStorage
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Adapter implementing ITokenStorage port
 * - Article IV (SSOT): SessionStorage as single source of truth for tokens
 * - Article V (SOLID): LSP - Substitutable for ITokenStorage
 * 
 * Note: Using sessionStorage for token persistence
 * For production with httpOnly cookies, this would integrate with backend
 */

import type { AuthToken } from '../../types/auth';
import type { ITokenStorage } from './ITokenStorage';
import { logger } from '../logging/LoggerFactory';

/**
 * Storage key for auth token
 */
const TOKEN_STORAGE_KEY = 'auth_token';

/**
 * TokenStorage class
 * 
 * Implements token storage using sessionStorage
 * Provides secure token persistence across page reloads
 */
export class TokenStorage implements ITokenStorage {
  /**
   * Save authentication token to sessionStorage
   * @param token - Auth token to save
   */
  saveToken(token: AuthToken): void {
    try {
      const tokenString = JSON.stringify(token);
      sessionStorage.setItem(TOKEN_STORAGE_KEY, tokenString);
      
      logger.debug('Token saved to storage', undefined, {
        component: 'TokenStorage',
        action: 'saveToken',
        userId: token.user.id,
      });
    } catch (error) {
      logger.error('Failed to save token to storage', error as Error, {
        component: 'TokenStorage',
        action: 'saveToken',
      });
      throw new Error('Failed to save authentication token');
    }
  }

  /**
   * Get authentication token from sessionStorage
   * @returns Saved token or null if not found or expired
   */
  getToken(): AuthToken | null {
    try {
      const tokenString = sessionStorage.getItem(TOKEN_STORAGE_KEY);
      
      if (!tokenString) {
        logger.debug('No token found in storage', undefined, {
          component: 'TokenStorage',
          action: 'getToken',
        });
        return null;
      }

      const token: AuthToken = JSON.parse(tokenString);

      // Check if token is expired
      const now = Date.now();
      if (token.expiresAt < now) {
        logger.warn('Token expired, removing from storage', undefined, {
          component: 'TokenStorage',
          action: 'getToken',
          expiresAt: new Date(token.expiresAt).toISOString(),
          now: new Date(now).toISOString(),
        });
        this.removeToken();
        return null;
      }

      logger.debug('Token retrieved from storage', undefined, {
        component: 'TokenStorage',
        action: 'getToken',
        userId: token.user.id,
      });

      return token;
    } catch (error) {
      logger.error('Failed to retrieve token from storage', error as Error, {
        component: 'TokenStorage',
        action: 'getToken',
      });
      
      // Clear corrupted token
      this.removeToken();
      return null;
    }
  }

  /**
   * Remove authentication token from sessionStorage
   */
  removeToken(): void {
    try {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      
      logger.debug('Token removed from storage', undefined, {
        component: 'TokenStorage',
        action: 'removeToken',
      });
    } catch (error) {
      logger.error('Failed to remove token from storage', error as Error, {
        component: 'TokenStorage',
        action: 'removeToken',
      });
    }
  }

  /**
   * Check if token exists in sessionStorage
   * @returns True if token exists (not checking expiration)
   */
  hasToken(): boolean {
    const tokenString = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    return tokenString !== null;
  }
}
