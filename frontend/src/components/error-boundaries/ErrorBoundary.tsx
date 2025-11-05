/**
 * ErrorBoundary Component
 * 
 * Production-ready error boundary for catching and handling React component errors
 * 
 * Features:
 * - Catches errors in child component tree
 * - Displays user-friendly fallback UI
 * - Logs errors via structured logging service
 * - Supports error recovery/retry
 * - Configurable fallback rendering
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): ErrorBoundary as adapter for error handling
 * - Article VII (Observability): Integrated structured logging
 * - Article V (SOLID): Single Responsibility - only handles UI error boundaries
 */

import React, { Component, type ReactNode } from 'react';
import { logger } from '../../services/logging/LoggerFactory';
import type { ErrorBoundaryState, ErrorBoundaryProps } from '../../types/errors';

// ErrorInfo type definition (React's ErrorInfo is a type-only export)
interface ErrorInfo {
  componentStack: string;
}

/**
 * ErrorBoundary class component
 * 
 * Note: Error boundaries must be class components as React doesn't support
 * error boundaries with hooks yet
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  /**
   * Static lifecycle method called when an error is thrown
   * Updates component state to trigger fallback UI
   */
  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  /**
   * Lifecycle method called after an error is caught
   * Used for logging and side effects
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to logging service with context
    logger.error(
      'Error Boundary caught an error',
      error,
      {
        component: this.props.componentName || 'ErrorBoundary',
        action: 'componentDidCatch',
        errorInfo: {
          componentStack: errorInfo.componentStack,
        },
      }
    );

    // Store error info in state for display
    this.setState({ errorInfo });

    // Call optional onError callback for parent notification
    if (this.props.onError) {
      this.props.onError({ error, errorInfo });
    }
  }

  /**
   * Reset error state to attempt recovery
   */
  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    // Call optional onReset callback
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  /**
   * Render method - shows fallback UI when error occurs
   */
  render(): ReactNode {
    if (this.state.hasError) {
      // If custom fallback provided, use it
      if (this.props.fallback) {
        return typeof this.props.fallback === 'function'
          ? this.props.fallback(this.state.error!, this.handleReset)
          : this.props.fallback;
      }

      // Default fallback UI
      return (
        <div
          role="alert"
          style={{
            padding: '2rem',
            margin: '2rem',
            border: '2px solid #ff4444',
            borderRadius: '8px',
            backgroundColor: '#fff5f5',
            fontFamily: 'system-ui, -apple-system, sans-serif',
          }}
        >
          <h2 style={{ color: '#cc0000', marginTop: 0 }}>
            Something went wrong
          </h2>
          <p style={{ color: '#666', marginBottom: '1.5rem' }}>
            We're sorry, but an unexpected error occurred. Please try one of the following:
          </p>
          <ul style={{ color: '#666', marginBottom: '1.5rem' }}>
            <li>Refresh the page</li>
            <li>Go back and try again</li>
            <li>Contact support if the problem persists</li>
          </ul>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              onClick={this.handleReset}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#0066cc',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '1rem',
              }}
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#666',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '1rem',
              }}
            >
              Refresh Page
            </button>
          </div>

          {/* Technical details - only show in development */}
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details style={{ marginTop: '2rem', color: '#333' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
                Technical Details (Development Only)
              </summary>
              <pre
                style={{
                  marginTop: '1rem',
                  padding: '1rem',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '4px',
                  overflow: 'auto',
                  fontSize: '0.875rem',
                }}
              >
                <strong>Error:</strong> {this.state.error.message}
                {'\n\n'}
                <strong>Stack:</strong>
                {'\n'}
                {this.state.error.stack}
                {this.state.errorInfo?.componentStack && (
                  <>
                    {'\n\n'}
                    <strong>Component Stack:</strong>
                    {'\n'}
                    {this.state.errorInfo.componentStack}
                  </>
                )}
              </pre>
            </details>
          )}
        </div>
      );
    }

    // No error - render children normally
    return this.props.children;
  }
}

export default ErrorBoundary;
