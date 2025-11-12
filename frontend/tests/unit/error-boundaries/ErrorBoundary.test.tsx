/**
 * ErrorBoundary Unit Tests
 * 
 * Test suite for ErrorBoundary component following TDD Red-Green-Refactor cycle
 * 
 * Constitution Compliance:
 * - Article III (TDD): Tests written BEFORE implementation
 * - Article VII (Observability): Verify error logging integration
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { ErrorBoundary } from '../../../src/components/error-boundaries/ErrorBoundary';
import { logger } from '../../../src/services/logging/LoggerFactory';

// Mock logger to verify it's called
vi.mock('../../../src/services/logging/LoggerFactory', () => ({
  logger: {
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  },
}));

// Component that throws an error for testing
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('Test error thrown by child component');
  }
  return <div>Child rendered successfully</div>;
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Suppress console.error in tests (React logs errors to console)
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  // T012: Test for ErrorBoundary rendering children when no error
  it('should render children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Child rendered successfully')).toBeInTheDocument();
  });

  // T013: Test for ErrorBoundary displaying fallback UI when child throws error
  it('should display fallback UI when child component throws error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // Should show error boundary fallback UI
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    // Should NOT render the child
    expect(screen.queryByText('Child rendered successfully')).not.toBeInTheDocument();
  });

  // T014: Test for ErrorBoundary calling onError callback when error occurs
  it('should call onError callback when error is caught', () => {
    const onErrorMock = vi.fn();

    render(
      <ErrorBoundary onError={onErrorMock}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // onError callback should be called with error details
    expect(onErrorMock).toHaveBeenCalledTimes(1);
    expect(onErrorMock).toHaveBeenCalledWith(
      expect.objectContaining({
        error: expect.any(Error),
        errorInfo: expect.any(Object),
      })
    );
  });

  // T015: Test for ErrorBoundary retry functionality
  it('should support retry functionality to reset error state', async () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // Initially should show error
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

    // Click retry button
    const retryButton = screen.getByRole('button', { name: /try again|retry/i });
    expect(retryButton).toBeInTheDocument();

    // After retry, should attempt to render children again
    // (In real scenario, the component would be fixed before retry)
    retryButton.click();

    // Re-render with non-throwing component
    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Child rendered successfully')).toBeInTheDocument();
  });

  // Additional test: Verify logger integration
  it('should log error to logging service when error is caught', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // Logger should be called with error details
    expect(logger.error).toHaveBeenCalled();
    const logCall = (logger.error as any).mock.calls[0];
    expect(logCall[0]).toMatch(/error/i); // Message
    expect(logCall[1]).toBeInstanceOf(Error); // Error object
  });

  // Additional test: Verify user-friendly error messages (no stack traces exposed)
  it('should display user-friendly error message without exposing technical details by default', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    // Should show friendly message
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    
    // Should NOT show raw error message or stack trace by default
    expect(screen.queryByText('Test error thrown by child component')).not.toBeInTheDocument();
  });
});
