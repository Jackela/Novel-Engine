/**
 * RouteErrorBoundary Component
 * 
 * Route-specific error boundary wrapper with navigation support
 * 
 * Features:
 * - Wraps individual route components for isolated error handling
 * - Provides navigation options (Go Back, Return to Home)
 * - Logs route information when errors occur
 * - Supports react-router integration
 * 
 * Constitution Compliance:
 * - Article II (Hexagonal): Adapter for route-level error handling
 * - Article VII (Observability): Enhanced logging with route context
 * - Article V (SOLID): Single Responsibility - route-specific error boundaries
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ErrorBoundary } from './ErrorBoundary';
import { logger } from '../../services/logging/LoggerFactory';
import type { ErrorBoundaryProps } from '../../types/errors';

interface RouteErrorBoundaryProps extends Omit<ErrorBoundaryProps, 'componentName' | 'fallback'> {
  routeName?: string;
  children: React.ReactNode;
}

const RouteErrorDetails: React.FC<{
  route: string;
  routeName?: string;
  error: Error;
}> = ({ route, routeName, error }) => (
  <details style={{ marginTop: '2rem', color: 'var(--color-text-secondary)' }}>
    <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
      Technical Details (Development Only)
    </summary>
    <pre
      style={{
        marginTop: '1rem',
        padding: '1rem',
        backgroundColor: 'var(--color-bg-secondary)',
        borderRadius: '4px',
        overflow: 'auto',
        fontSize: '0.875rem',
      }}
    >
      <strong>Route:</strong> {route}
      {'\n'}
      <strong>Route Name:</strong> {routeName || 'Unknown'}
      {'\n\n'}
      <strong>Error:</strong> {error.message}
      {'\n\n'}
      <strong>Stack:</strong>
      {'\n'}
      {error.stack}
    </pre>
  </details>
);

const RouteErrorActions: React.FC<{
  onBack: () => void;
  onHome: () => void;
  onReset: () => void;
}> = ({ onBack, onHome, onReset }) => (
  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
    <button
      onClick={onBack}
      style={{
        padding: '0.5rem 1rem',
        backgroundColor: 'var(--color-info)',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1rem',
      }}
    >
      Go Back
    </button>
    <button
      onClick={onHome}
      style={{
        padding: '0.5rem 1rem',
        backgroundColor: 'var(--color-info)',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1rem',
      }}
    >
      Return to Home
    </button>
    <button
      onClick={onReset}
      style={{
        padding: '0.5rem 1rem',
        backgroundColor: 'var(--color-text-tertiary)',
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
        backgroundColor: 'var(--color-text-tertiary)',
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
);

const RouteFallback: React.FC<{
  error: Error;
  reset: () => void;
  route: string;
  routeName?: string;
  onBack: () => void;
  onHome: () => void;
}> = ({ error, reset, route, routeName, onBack, onHome }) => (
  <div
    role="alert"
    style={{
      padding: '2rem',
      margin: '2rem',
      border: '2px solid var(--color-error)',
      borderRadius: '8px',
      backgroundColor: 'var(--color-error-bg)',
      fontFamily: 'var(--font-primary)',
    }}
  >
    <h2 style={{ color: 'var(--color-error)', marginTop: 0 }}>
      Something went wrong on this page
    </h2>
    <p style={{ color: 'var(--color-text-tertiary)', marginBottom: '1.5rem' }}>
      We're sorry, but an error occurred while loading this page. You can:
    </p>
    <ul style={{ color: 'var(--color-text-tertiary)', marginBottom: '1.5rem' }}>
      <li>Try going back to the previous page</li>
      <li>Return to the home page</li>
      <li>Refresh the page</li>
    </ul>
    <RouteErrorActions onBack={onBack} onHome={onHome} onReset={reset} />

    {process.env.NODE_ENV === 'development' && (
      <RouteErrorDetails route={route} routeName={routeName} error={error} />
    )}
  </div>
);

/**
 * RouteErrorBoundary wrapper component
 * 
 * Wraps ErrorBoundary with route-specific navigation capabilities
 */
export const RouteErrorBoundary: React.FC<RouteErrorBoundaryProps> = ({ 
  routeName,
  children,
  onError,
  ...props 
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  // Enhanced error handler with route context
  const handleError = (errorDetails: { error: Error; errorInfo: { componentStack: string } }) => {
    // Log route-specific error context
    logger.error(
      'Route Error Boundary caught an error',
      errorDetails.error,
      {
        component: routeName || 'RouteErrorBoundary',
        action: 'routeError',
        route: location.pathname,
        routeName: routeName,
        errorInfo: {
          componentStack: errorDetails.errorInfo.componentStack,
        },
      }
    );

    // Call parent onError if provided
    if (onError) {
      onError(errorDetails);
    }
  };

  // Custom fallback UI with navigation options
  const fallback = (error: Error, reset: () => void) => {
    return (
      <RouteFallback
        error={error}
        reset={reset}
        route={location.pathname}
        routeName={routeName}
        onBack={() => navigate(-1)}
        onHome={() => navigate('/')}
      />
    );
  };

  return (
    <ErrorBoundary
      componentName={routeName || `Route: ${location.pathname}`}
      fallback={fallback}
      onError={handleError}
      {...props}
    >
      {children}
    </ErrorBoundary>
  );
};

export default RouteErrorBoundary;
