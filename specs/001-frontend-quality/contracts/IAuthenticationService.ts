/**
 * IAuthenticationService Interface - Authentication Port
 * 
 * Defines the contract for authentication services.
 * Supports JWT-based authentication with automatic token refresh.
 * 
 * Constitution Compliance:
 * - Article II (Ports & Adapters): Port interface for authentication
 * - Article IV (SSOT): Token storage as single source of auth state
 * - Article V (SOLID): Interface Segregation Principle
 */

import type { AuthToken, LoginRequest, LoginResponse, AuthState } from '../../../frontend/src/types/auth';

/**
 * Authentication service interface
 * 
 * Implementations:
 * - JWTAuthService: JWT-based authentication with httpOnly cookies
 * - MockAuthService: Mock authentication for testing
 */
export interface IAuthenticationService {
  /**
   * Authenticate user with credentials
   * 
   * @param request - Login credentials (username/email + password)
   * @returns Authentication token on success
   * @throws Error if authentication fails
   * 
   * @example
   * const token = await authService.login({
   *   username: 'john_doe',
   *   password: 'securePassword123',
   *   rememberMe: true,
   * });
   */
  login(request: LoginRequest): Promise<AuthToken>;

  /**
   * Log out current user
   * 
   * Clears tokens from storage and invalidates session.
   * 
   * @throws Error if logout fails
   * 
   * @example
   * await authService.logout();
   */
  logout(): Promise<void>;

  /**
   * Refresh access token using refresh token
   * 
   * Automatically called when access token expires or is about to expire.
   * 
   * @returns New authentication token
   * @throws Error if refresh fails (user must re-login)
   * 
   * @example
   * const newToken = await authService.refreshToken();
   */
  refreshToken(): Promise<AuthToken>;

  /**
   * Get current authentication token
   * 
   * @returns Current token or null if not authenticated
   * 
   * @example
   * const token = authService.getToken();
   * if (token) {
   *   console.log('User is authenticated:', token.user.username);
   * }
   */
  getToken(): AuthToken | null;

  /**
   * Check if user is currently authenticated
   * 
   * @returns True if user has valid token, false otherwise
   * 
   * @example
   * if (authService.isAuthenticated()) {
   *   // Show authenticated UI
   * } else {
   *   // Redirect to login
   * }
   */
  isAuthenticated(): boolean;

  /**
   * Check if token is expired or about to expire
   * 
   * @param token - Token to check (uses current token if not provided)
   * @param bufferSeconds - Seconds before expiration to consider expired (default: 300)
   * @returns True if token is expired or will expire within buffer time
   * 
   * @example
   * if (authService.isTokenExpired(null, 300)) {
   *   // Token expires in < 5 minutes, refresh it
   *   await authService.refreshToken();
   * }
   */
  isTokenExpired(token?: AuthToken | null, bufferSeconds?: number): boolean;

  /**
   * Get current authentication state
   * 
   * @returns Current auth state (authenticated, refreshing, error, etc.)
   * 
   * @example
   * const state = authService.getAuthState();
   * console.log('Auth state:', state.isAuthenticated, state.isRefreshing);
   */
  getAuthState(): AuthState;

  /**
   * Subscribe to authentication state changes
   * 
   * Callback is called whenever auth state changes (login, logout, refresh).
   * 
   * @param callback - Callback to invoke on state change
   * @returns Unsubscribe function
   * 
   * @example
   * const unsubscribe = authService.onAuthStateChange((state) => {
   *   console.log('Auth state changed:', state.isAuthenticated);
   * });
   * // Later: unsubscribe()
   */
  onAuthStateChange(callback: (state: AuthState) => void): () => void;

  /**
   * Initialize authentication service
   * 
   * Checks for existing token in storage and validates it.
   * Should be called once at application startup.
   * 
   * @returns Promise that resolves when initialization is complete
   * 
   * @example
   * await authService.initialize();
   * // Now authService.isAuthenticated() is accurate
   */
  initialize(): Promise<void>;

  /**
   * Manually set authentication token
   * 
   * Useful for testing or when receiving token from external source.
   * 
   * @param token - Authentication token to set
   * 
   * @example
   * authService.setToken(tokenFromOAuth);
   */
  setToken(token: AuthToken): void;

  /**
   * Clear authentication token
   * 
   * Similar to logout but doesn't call backend API.
   * Useful for token expiration handling.
   * 
   * @example
   * authService.clearToken();
   */
  clearToken(): void;
}

/**
 * Token storage interface
 * 
 * Abstracts token persistence mechanism (cookies, sessionStorage, localStorage).
 */
export interface ITokenStorage {
  /**
   * Save authentication token
   * 
   * @param token - Token to save
   * 
   * @example
   * tokenStorage.saveToken(authToken);
   */
  saveToken(token: AuthToken): void;

  /**
   * Retrieve saved authentication token
   * 
   * @returns Saved token or null if not found
   * 
   * @example
   * const token = tokenStorage.getToken();
   */
  getToken(): AuthToken | null;

  /**
   * Remove saved authentication token
   * 
   * @example
   * tokenStorage.removeToken();
   */
  removeToken(): void;

  /**
   * Check if token exists in storage
   * 
   * @returns True if token exists
   * 
   * @example
   * if (tokenStorage.hasToken()) {
   *   // Token exists, try to use it
   * }
   */
  hasToken(): boolean;
}

/**
 * Authentication service factory interface
 */
export interface IAuthenticationServiceFactory {
  /**
   * Create authentication service instance
   * 
   * @returns Authentication service implementation
   */
  create(): IAuthenticationService;

  /**
   * Create authentication service with custom configuration
   * 
   * @param config - Custom configuration
   * @returns Configured authentication service
   */
  createWithConfig(config: AuthServiceConfig): IAuthenticationService;
}

/**
 * Authentication service configuration
 */
export interface AuthServiceConfig {
  /** Base URL for authentication API */
  apiBaseUrl: string;
  
  /** Token storage implementation */
  tokenStorage: ITokenStorage;
  
  /** Auto-refresh buffer time (seconds before expiration) */
  refreshBufferSeconds: number;
  
  /** Enable automatic token refresh */
  enableAutoRefresh: boolean;
  
  /** Maximum refresh retry attempts */
  maxRefreshRetries: number;
  
  /** Login endpoint path */
  loginEndpoint: string;
  
  /** Logout endpoint path */
  logoutEndpoint: string;
  
  /** Refresh endpoint path */
  refreshEndpoint: string;
}
