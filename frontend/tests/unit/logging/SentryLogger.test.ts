/**
 * SentryLogger Unit Tests
 * 
 * Test suite for production SentryLogger implementation following TDD Red-Green-Refactor cycle
 * 
 * Constitution Compliance:
 * - Article III (TDD): Tests written BEFORE implementation
 * - Article VII (Observability): Verify production error tracking integration
 * - Article V (SOLID): LSP - SentryLogger implements ILogger interface
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LogLevel } from '../../../src/types/logging';

// Mock Sentry SDK
const mockCaptureException = vi.fn();
const mockCaptureMessage = vi.fn();
const mockSetUser = vi.fn();
const mockSetTag = vi.fn();
const mockSetContext = vi.fn();

vi.mock('@sentry/browser', () => ({
  captureException: mockCaptureException,
  captureMessage: mockCaptureMessage,
  setUser: mockSetUser,
  setTag: mockSetTag,
  setContext: mockSetContext,
  Severity: {
    Debug: 'debug',
    Info: 'info',
    Warning: 'warning',
    Error: 'error',
  },
}));

// Import SentryLogger AFTER mocking
import { SentryLogger } from '../../../src/services/logging/SentryLogger';

describe('SentryLogger', () => {
  let logger: SentryLogger;

  beforeEach(() => {
    vi.clearAllMocks();
    logger = new SentryLogger({ minLevel: LogLevel.DEBUG });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // T027: Test for SentryLogger sending errors to Sentry
  describe('Error Reporting', () => {
    it('should send error to Sentry when error() is called', () => {
      const error = new Error('Test error');
      const context = { component: 'TestComponent', action: 'testAction' };

      logger.error('Test error message', error, context);

      expect(mockCaptureException).toHaveBeenCalledTimes(1);
      expect(mockCaptureException).toHaveBeenCalledWith(error, expect.any(Object));
    });

    it('should send error with context metadata to Sentry', () => {
      const error = new Error('Test error with context');
      const context = {
        component: 'TestComponent',
        action: 'testAction',
        userId: 'user123',
      };

      logger.error('Test error message', error, context);

      expect(mockSetContext).toHaveBeenCalledWith('logContext', context);
      expect(mockCaptureException).toHaveBeenCalled();
    });

    it('should send error messages without Error object to Sentry', () => {
      const context = { component: 'TestComponent' };

      logger.error('Error message without exception', undefined, context);

      expect(mockCaptureMessage).toHaveBeenCalledWith(
        'Error message without exception',
        expect.any(Object)
      );
    });
  });

  // T028: Test for production log level filtering (only WARN/ERROR)
  describe('Production Log Level Filtering', () => {
    it('should filter out DEBUG logs in production mode', () => {
      const productionLogger = new SentryLogger({ minLevel: LogLevel.WARN });

      productionLogger.debug('Debug message');

      expect(mockCaptureMessage).not.toHaveBeenCalled();
    });

    it('should filter out INFO logs in production mode', () => {
      const productionLogger = new SentryLogger({ minLevel: LogLevel.WARN });

      productionLogger.info('Info message');

      expect(mockCaptureMessage).not.toHaveBeenCalled();
    });

    it('should allow WARN logs in production mode', () => {
      const productionLogger = new SentryLogger({ minLevel: LogLevel.WARN });

      productionLogger.warn('Warning message');

      expect(mockCaptureMessage).toHaveBeenCalledWith(
        'Warning message',
        expect.any(Object)
      );
    });

    it('should allow ERROR logs in production mode', () => {
      const productionLogger = new SentryLogger({ minLevel: LogLevel.ERROR });
      const error = new Error('Production error');

      productionLogger.error('Error message', error);

      expect(mockCaptureException).toHaveBeenCalledWith(error, expect.any(Object));
    });
  });

  describe('Log Level Configuration', () => {
    it('should respect minLevel configuration for all log levels', () => {
      const warnLogger = new SentryLogger({ minLevel: LogLevel.WARN });

      warnLogger.debug('Debug');
      warnLogger.info('Info');
      warnLogger.warn('Warn');
      warnLogger.error('Error', new Error('test'));

      // Only WARN and ERROR should be sent
      expect(mockCaptureMessage).toHaveBeenCalledTimes(1); // warn
      expect(mockCaptureException).toHaveBeenCalledTimes(1); // error
    });
  });

  describe('Context and Metadata', () => {
    it('should set user context when userId is provided', () => {
      const context = { userId: 'user123', component: 'TestComponent' };

      logger.info('User action', undefined, context);

      expect(mockSetUser).toHaveBeenCalledWith({ id: 'user123' });
    });

    it('should set tags for component and action', () => {
      const context = { component: 'TestComponent', action: 'testAction' };

      logger.warn('Test warning', undefined, context);

      expect(mockSetTag).toHaveBeenCalledWith('component', 'TestComponent');
      expect(mockSetTag).toHaveBeenCalledWith('action', 'testAction');
    });
  });

  describe('Sanitization Integration', () => {
    it('should sanitize sensitive data before sending to Sentry', () => {
      const context = {
        component: 'AuthComponent',
        password: 'secret123',
        token: 'Bearer abc123',
      };

      logger.error('Auth error', new Error('test'), context);

      // Verify context was sanitized (password/token should be redacted)
      const setContextCall = mockSetContext.mock.calls[0];
      expect(setContextCall).toBeDefined();
      if (setContextCall) {
        const sanitizedContext = setContextCall[1];
        expect(sanitizedContext.password).toBe('[REDACTED]');
        expect(sanitizedContext.token).toBe('[REDACTED]');
      }
    });
  });
});
