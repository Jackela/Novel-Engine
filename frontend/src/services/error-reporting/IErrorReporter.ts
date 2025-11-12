/**
 * IErrorReporter Interface
 * 
 * Port for error reporting and tracking services (Hexagonal Architecture)
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Port interface for error reporting
 * - Article V (SOLID): ISP - Interface Segregation Principle
 * - Article VII (Observability): Error tracking and reporting
 */

/**
 * Error severity levels for classification and prioritization
 */
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

/**
 * User context for error attribution
 */
export interface UserContext {
  id?: string;
  username?: string;
  email?: string;
  [key: string]: unknown;
}

/**
 * Error context with metadata
 */
export interface ErrorContext {
  component?: string;
  action?: string;
  severity?: ErrorSeverity;
  tags?: Record<string, string>;
  extra?: Record<string, unknown>;
  userId?: string;
  sessionId?: string;
  timestamp?: string;
}

/**
 * Error boundary specific context
 */
export interface BoundaryErrorContext extends ErrorContext {
  componentStack?: string;
  boundaryName?: string;
}

/**
 * IErrorReporter interface
 * 
 * Defines contract for error reporting services (Sentry, LogRocket, etc.)
 */
export interface IErrorReporter {
  /**
   * Report a general error
   * @param error - Error object to report
   * @param context - Additional context for the error
   */
  reportError(error: Error, context?: ErrorContext): void;

  /**
   * Report an error caught by error boundary
   * @param error - Error object caught by boundary
   * @param context - Boundary-specific context
   */
  reportBoundaryError(error: Error, context: BoundaryErrorContext): void;

  /**
   * Set user context for error attribution
   * @param user - User information
   */
  setUser(user: UserContext | null): void;

  /**
   * Add breadcrumb for error context trail
   * @param message - Breadcrumb message
   * @param category - Breadcrumb category
   * @param data - Additional data
   */
  addBreadcrumb?(message: string, category?: string, data?: Record<string, unknown>): void;

  /**
   * Set custom context for errors
   * @param key - Context key
   * @param value - Context value
   */
  setContext?(key: string, value: Record<string, unknown>): void;
}
