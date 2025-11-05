/**
 * IErrorReporter Interface - Error Tracking Port
 * 
 * Defines the contract for error reporting services (Sentry, CloudWatch, etc.).
 * Supports structured error reporting with context and severity levels.
 * 
 * Constitution Compliance:
 * - Article II (Ports & Adapters): Port interface for error reporting
 * - Article V (SOLID): Interface Segregation Principle
 * - Article VII (Observability): Error tracking and monitoring
 */

import type { ErrorReport } from '../../../frontend/src/types/errors';

/**
 * Error reporting service interface
 * 
 * Implementations:
 * - SentryReporter: Send errors to Sentry for tracking and alerting
 * - CloudWatchReporter: Send errors to AWS CloudWatch Logs
 * - ConsoleReporter: Log errors to console (development fallback)
 * - NullReporter: No-op reporter for testing
 */
export interface IErrorReporter {
  /**
   * Report an error to the tracking service
   * 
   * @param error - Error object to report
   * @param context - Additional context about where/when error occurred
   * @param severity - Error severity level (fatal/error/warning/info)
   * 
   * @example
   * errorReporter.reportError(
   *   new Error('Failed to load data'),
   *   { component: 'Dashboard', action: 'fetchData', route: '/dashboard' },
   *   'error'
   * );
   */
  reportError(
    error: Error,
    context?: ErrorContext,
    severity?: ErrorSeverity
  ): Promise<void>;

  /**
   * Report error boundary error with React error info
   * 
   * @param error - Error object
   * @param errorInfo - React error info with component stack
   * @param boundaryName - Name of error boundary that caught error
   * 
   * @example
   * errorReporter.reportBoundaryError(
   *   error,
   *   errorInfo,
   *   'RootErrorBoundary'
   * );
   */
  reportBoundaryError(
    error: Error,
    errorInfo: React.ErrorInfo,
    boundaryName: string
  ): Promise<void>;

  /**
   * Report custom error with full ErrorReport structure
   * 
   * @param report - Complete error report with all context
   * 
   * @example
   * errorReporter.reportCustom({
   *   message: 'Payment processing failed',
   *   name: 'PaymentError',
   *   severity: 'error',
   *   context: { component: 'CheckoutForm', action: 'submitPayment' },
   *   timestamp: new Date().toISOString(),
   * });
   */
  reportCustom(report: ErrorReport): Promise<void>;

  /**
   * Set user context for error reports
   * 
   * Associates all subsequent error reports with this user.
   * Useful for tracking errors per user.
   * 
   * @param userId - User ID (anonymized if needed)
   * @param username - Username (optional)
   * @param email - User email (optional, hashed for privacy)
   * 
   * @example
   * errorReporter.setUser('user-123', 'john_doe');
   */
  setUser(userId: string, username?: string, email?: string): void;

  /**
   * Clear user context (e.g., on logout)
   * 
   * @example
   * errorReporter.clearUser();
   */
  clearUser(): void;

  /**
   * Add breadcrumb for error tracking
   * 
   * Breadcrumbs help reconstruct user actions leading to error.
   * 
   * @param message - Breadcrumb message
   * @param category - Category (navigation, user-action, api-call, etc.)
   * @param data - Additional data (optional)
   * 
   * @example
   * errorReporter.addBreadcrumb(
   *   'User clicked submit button',
   *   'user-action',
   *   { formId: 'login-form' }
   * );
   */
  addBreadcrumb(
    message: string,
    category: BreadcrumbCategory,
    data?: Record<string, unknown>
  ): void;

  /**
   * Set custom tag for error filtering/grouping
   * 
   * @param key - Tag key
   * @param value - Tag value
   * 
   * @example
   * errorReporter.setTag('feature', 'knowledge-management');
   */
  setTag(key: string, value: string): void;

  /**
   * Capture exception (alias for reportError with 'error' severity)
   * 
   * @param error - Error object
   * @param context - Additional context
   * 
   * @example
   * errorReporter.captureException(error, { component: 'Dashboard' });
   */
  captureException(error: Error, context?: ErrorContext): Promise<void>;

  /**
   * Capture message (non-error event)
   * 
   * @param message - Message to capture
   * @param severity - Severity level
   * @param context - Additional context
   * 
   * @example
   * errorReporter.captureMessage(
   *   'WebSocket connection lost',
   *   'warning',
   *   { component: 'Dashboard', reconnectAttempt: 3 }
   * );
   */
  captureMessage(
    message: string,
    severity: ErrorSeverity,
    context?: ErrorContext
  ): Promise<void>;
}

/**
 * Error severity levels
 */
export type ErrorSeverity = 'fatal' | 'error' | 'warning' | 'info';

/**
 * Breadcrumb categories for user action tracking
 */
export type BreadcrumbCategory =
  | 'navigation'
  | 'user-action'
  | 'api-call'
  | 'state-change'
  | 'console'
  | 'network'
  | 'error';

/**
 * Error context for additional information
 */
export interface ErrorContext {
  /** Component or module where error occurred */
  component?: string;
  
  /** User action that triggered error */
  action?: string;
  
  /** Route/path where error occurred */
  route?: string;
  
  /** User ID (anonymized) */
  userId?: string;
  
  /** Session ID for correlation */
  sessionId?: string;
  
  /** Browser information */
  browser?: {
    name: string;
    version: string;
    os: string;
  };
  
  /** Additional metadata (sanitized) */
  extra?: Record<string, unknown>;
}

/**
 * Error reporter factory interface
 */
export interface IErrorReporterFactory {
  /**
   * Create error reporter instance
   * 
   * @returns Error reporter implementation based on environment
   */
  create(): IErrorReporter;

  /**
   * Create error reporter with custom configuration
   * 
   * @param config - Custom configuration
   * @returns Configured error reporter
   */
  createWithConfig(config: ErrorReporterConfig): IErrorReporter;
}

/**
 * Error reporter configuration
 */
export interface ErrorReporterConfig {
  /** Sentry DSN (if using Sentry) */
  sentryDsn?: string;
  
  /** Environment (dev/staging/production) */
  environment: string;
  
  /** Application release version */
  release?: string;
  
  /** Sample rate (0.0 to 1.0) */
  sampleRate?: number;
  
  /** Whether to attach stack traces */
  attachStacktrace?: boolean;
  
  /** Whether to enable in current environment */
  enabled: boolean;
}
