/**
 * SentryLogger Implementation
 * 
 * Production logger that integrates with Sentry for error tracking
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Adapter implementing ILogger port
 * - Article V (SOLID): LSP - Substitutable for ILogger interface
 * - Article VII (Observability): Production error tracking and monitoring
 */

import * as Sentry from '@sentry/browser';
import type { ILogger } from './ILogger';
import type { LogLevel, LogContext, LoggerConfig } from '@/types/logging';
import { Sanitizer } from './Sanitizer';

/**
 * Map LogLevel to Sentry Severity
 */
const LOG_LEVEL_TO_SENTRY_SEVERITY: Record<LogLevel, Sentry.SeverityLevel> = {
  DEBUG: 'debug',
  INFO: 'info',
  WARN: 'warning',
  ERROR: 'error',
};

/**
 * SentryLogger class
 * 
 * Production logger that sends errors and messages to Sentry
 * with automatic sanitization and context enrichment
 */
export class SentryLogger implements ILogger {
  private minLevel: LogLevel;

  constructor(config: LoggerConfig) {
    this.minLevel = config.minLevel || 'INFO';
  }

  /**
   * Check if log level should be logged based on minLevel
   */
  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['DEBUG', 'INFO', 'WARN', 'ERROR'];
    const currentLevelIndex = levels.indexOf(level);
    const minLevelIndex = levels.indexOf(this.minLevel);
    return currentLevelIndex >= minLevelIndex;
  }

  /**
   * Set Sentry context from log context
   */
  private setContextInSentry(context?: LogContext): void {
    if (!context) return;

    // Sanitize context before sending to Sentry
    const sanitizedContext = Sanitizer.sanitize(context);

    // Set user if userId is present
    if (context.userId) {
      Sentry.setUser({ id: context.userId });
    }

    // Set tags for component and action
    if (context.component) {
      Sentry.setTag('component', context.component);
    }
    if (context.action) {
      Sentry.setTag('action', context.action);
    }

    // Set full context
    Sentry.setContext('logContext', sanitizedContext);
  }

  /**
   * Log debug message (filtered in production)
   */
  debug(message: string, error?: Error, context?: LogContext): void {
    if (!this.shouldLog('DEBUG')) return;

    this.setContextInSentry(context);
    Sentry.captureMessage(message, 'debug');
  }

  /**
   * Log info message (filtered in production)
   */
  info(message: string, error?: Error, context?: LogContext): void {
    if (!this.shouldLog('INFO')) return;

    this.setContextInSentry(context);
    Sentry.captureMessage(message, 'info');
  }

  /**
   * Log warning message
   */
  warn(message: string, error?: Error, context?: LogContext): void {
    if (!this.shouldLog('WARN')) return;

    this.setContextInSentry(context);

    if (error) {
      Sentry.captureException(error, {
        level: 'warning',
      });
    } else {
      Sentry.captureMessage(message, 'warning');
    }
  }

  /**
   * Log error message
   */
  error(message: string, error?: Error, context?: LogContext): void {
    if (!this.shouldLog('ERROR')) return;

    this.setContextInSentry(context);

    if (error) {
      Sentry.captureException(error, {
        level: 'error',
      });
    } else {
      Sentry.captureMessage(message, 'error');
    }
  }
}
