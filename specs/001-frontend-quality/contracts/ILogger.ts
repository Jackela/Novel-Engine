/**
 * ILogger Interface - Logging Service Port
 * 
 * Defines the contract for logging services in the application.
 * Supports environment-aware logging with automatic sanitization.
 * 
 * Constitution Compliance:
 * - Article II (Ports & Adapters): Port interface for logging
 * - Article V (SOLID): Interface Segregation Principle
 * - Article VII (Observability): Structured logging contract
 */

import type { LogLevel, LogContext, LogEntry } from '../../../frontend/src/types/logging';

/**
 * Logging service interface
 * 
 * Implementations:
 * - ConsoleLogger: Development logging to browser console
 * - SentryLogger: Production logging to Sentry/error tracking service
 * - NullLogger: No-op logger for testing
 */
export interface ILogger {
  /**
   * Log debug message (development only, auto-removed in production)
   * 
   * @param message - Human-readable debug message
   * @param context - Additional structured context (will be sanitized)
   * 
   * @example
   * logger.debug('User clicked submit button', { 
   *   component: 'LoginForm', 
   *   action: 'submit' 
   * });
   */
  debug(message: string, context?: LogContext): void;

  /**
   * Log informational message (development only, auto-removed in production)
   * 
   * @param message - Human-readable info message
   * @param context - Additional structured context (will be sanitized)
   * 
   * @example
   * logger.info('API request started', { 
   *   component: 'KnowledgeAPI', 
   *   endpoint: '/api/v1/knowledge/entries' 
   * });
   */
  info(message: string, context?: LogContext): void;

  /**
   * Log warning message (both dev and production)
   * 
   * @param message - Human-readable warning message
   * @param context - Additional structured context (will be sanitized)
   * 
   * @example
   * logger.warn('API response slow', { 
   *   component: 'KnowledgeAPI', 
   *   duration: 2500 
   * });
   */
  warn(message: string, context?: LogContext): void;

  /**
   * Log error message (both dev and production)
   * 
   * @param message - Human-readable error message
   * @param error - Error object (optional, for exception details)
   * @param context - Additional structured context (will be sanitized)
   * 
   * @example
   * logger.error('Failed to create knowledge entry', error, { 
   *   component: 'KnowledgeAPI', 
   *   action: 'createEntry' 
   * });
   */
  error(message: string, error?: Error, context?: LogContext): void;

  /**
   * Create structured log entry (internal use, for custom log processing)
   * 
   * @param level - Log severity level
   * @param message - Human-readable message
   * @param context - Additional structured context (will be sanitized)
   * @param error - Error object (optional)
   * @returns Structured log entry with sanitized context
   */
  createLogEntry(
    level: LogLevel,
    message: string,
    context?: LogContext,
    error?: Error
  ): LogEntry;

  /**
   * Sanitize sensitive data from context object
   * 
   * Removes or masks:
   * - password, apiKey, secret, authorization
   * - Email addresses (partial masking)
   * - Tokens (show last 4 chars)
   * - Credit cards, SSN
   * 
   * @param context - Context object to sanitize
   * @returns Sanitized context safe for logging
   * 
   * @example
   * const sanitized = logger.sanitize({ 
   *   password: 'secret123', 
   *   email: 'john@example.com' 
   * });
   * // Result: { password: '***', email: 'jo**@example.com' }
   */
  sanitize(context: Record<string, unknown>): Record<string, unknown>;

  /**
   * Set minimum log level (for runtime configuration)
   * 
   * @param level - Minimum log level to output
   * 
   * @example
   * logger.setMinLevel(LogLevel.WARN); // Only WARN and ERROR
   */
  setMinLevel(level: LogLevel): void;

  /**
   * Get current minimum log level
   * 
   * @returns Current minimum log level
   */
  getMinLevel(): LogLevel;
}

/**
 * Logger factory interface
 * 
 * Creates appropriate logger implementation based on environment.
 */
export interface ILoggerFactory {
  /**
   * Create logger instance
   * 
   * @returns Logger implementation (ConsoleLogger for dev, SentryLogger for prod)
   */
  create(): ILogger;

  /**
   * Create logger with custom configuration
   * 
   * @param config - Custom logger configuration
   * @returns Configured logger instance
   */
  createWithConfig(config: Partial<LoggerConfig>): ILogger;
}

/**
 * Logger configuration
 */
export interface LoggerConfig {
  /** Minimum log level to output */
  minLevel: LogLevel;
  
  /** Environment (dev/prod) */
  environment: 'development' | 'production';
  
  /** Whether to include timestamps */
  includeTimestamp: boolean;
  
  /** Whether to include component names */
  includeComponent: boolean;
  
  /** Whether to send to remote service */
  enableRemoteLogging: boolean;
  
  /** Remote service URL (if enabled) */
  remoteUrl?: string;
}
