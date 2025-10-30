import React from 'react';
import './ErrorDisplay.css';

/**
 * ErrorDisplay Component
 * 
 * Displays user-friendly error messages with recovery suggestions
 * Features:
 * - Different severity levels (error, warning, info)
 * - Actionable recovery suggestions
 * - Retry mechanisms
 * - Collapsible technical details
 */
type Severity = 'error' | 'warning' | 'info';

export interface DisplayError {
  title: string;
  message: string;
  suggestions?: string[];
  severity?: Severity;
  recoverable?: boolean;
  retriesExhausted?: boolean;
  originalError?: unknown;
  timestamp?: string | number;
}

interface ErrorDisplayProps {
  error?: DisplayError | null;
  onRetry?: () => void;
  onDismiss?: () => void;
  showTechnicalDetails?: boolean;
  className?: string;
}

function ErrorDisplay({ 
  error, 
  onRetry, 
  onDismiss, 
  showTechnicalDetails = false,
  className = '' 
}: ErrorDisplayProps) {
  const [showDetails, setShowDetails] = React.useState(false);

  if (!error) return null;

  const {
    title,
    message,
    suggestions = [],
    severity = 'error',
    recoverable = true,
    retriesExhausted = false,
    originalError,
    timestamp
  } = error;

  const severityIcons: Record<Severity, string> = {
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };

  const severityColors: Record<Severity, string> = {
    error: 'error',
    warning: 'warning', 
    info: 'info'
  };

  return (
    <div className={`error-display ${severityColors[severity]} ${className}`}>
      <div className="error-header">
        <div className="error-icon">
          {severityIcons[severity]}
        </div>
        <div className="error-content">
          <h3 className="error-title">{title}</h3>
          <p className="error-message">{message}</p>
        </div>
        {onDismiss && (
          <button 
            onClick={onDismiss}
            className="error-dismiss"
            aria-label="Dismiss error"
          >
            ×
          </button>
        )}
      </div>

      {suggestions.length > 0 && (
        <div className="error-suggestions">
          <h4>💡 How to fix this:</h4>
          <ul>
            {suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="error-actions">
        {recoverable && onRetry && !retriesExhausted && (
          <button 
            onClick={onRetry}
            className="btn-retry"
          >
            🔄 Try Again
          </button>
        )}
        
        {retriesExhausted && (
          <div className="retry-exhausted">
            <span>⏰ Multiple attempts failed. Please check the suggestions above.</span>
          </div>
        )}

        <button
          onClick={() => window.location.reload()}
          className="btn-refresh"
        >
          🔃 Refresh Page
        </button>

        <button
          onClick={() => {
            // Clear local storage and reload
            localStorage.clear();
            window.location.reload();
          }}
          className="btn-reset"
        >
          🗑️ Reset & Reload
        </button>
      </div>

      {showTechnicalDetails && originalError && (
        <div className="error-technical">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="technical-toggle"
          >
            {showDetails ? '👆 Hide' : '🔍 Show'} technical details
          </button>
          
          {showDetails && (
            <div className="technical-details">
              <div className="technical-section">
                <h5>Error Details:</h5>
                <pre>{JSON.stringify({
                  message: originalError.message,
                  type: originalError.constructor.name,
                  code: originalError.code,
                  status: originalError.response?.status,
                  timestamp: timestamp
                }, null, 2)}</pre>
              </div>
              
              {originalError.stack && (
                <div className="technical-section">
                  <h5>Stack Trace:</h5>
                  <pre>{originalError.stack}</pre>
                </div>
              )}
              
              <div className="technical-section">
                <h5>Browser Info:</h5>
                <pre>{JSON.stringify({
                  userAgent: navigator.userAgent,
                  url: window.location.href,
                  timestamp: new Date().toISOString()
                }, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="error-footer">
        <small>
          If this problem persists, please report it with the technical details above.
        </small>
      </div>
    </div>
  );
}

/**
 * Retry Status Component
 * Shows current retry attempt progress
 */
export interface RetryStatusState { attempt: number; maxAttempts: number; delay: number }

export function RetryStatus({ retryStatus, onCancel }: { retryStatus?: RetryStatusState | null; onCancel?: () => void }) {
  if (!retryStatus) return null;

  const { attempt, maxAttempts, delay } = retryStatus;
  
  return (
    <div className="retry-status">
      <div className="retry-content">
        <div className="retry-spinner"></div>
        <div className="retry-text">
          <p>Retrying... (attempt {attempt} of {maxAttempts})</p>
          <div className="retry-progress">
            <div 
              className="retry-progress-bar"
              style={{ 
                animationDuration: `${delay}ms`,
                width: `${(attempt / maxAttempts) * 100}%`
              }}
            ></div>
          </div>
        </div>
      </div>
      {onCancel && (
        <button onClick={onCancel} className="retry-cancel">
          Cancel
        </button>
      )}
    </div>
  );
}

/**
 * Global Error Boundary Component
 * Catches JavaScript errors anywhere in the component tree
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { 
      hasError: true, 
      error: {
        title: 'Application Error',
        message: 'Something went wrong in the application.',
        suggestions: [
          'Try refreshing the page',
          'Clear your browser cache',
          'Check the browser console for more details',
          'Report this issue if it continues'
        ],
        severity: 'error',
        recoverable: true,
        originalError: error
      }
    };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error Boundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <ErrorDisplay
            error={this.state.error}
            onRetry={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            showTechnicalDetails={true}
          />
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorDisplay;
