import type { ErrorInfo, ReactNode } from 'react';

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorTimestamp: string | null;
  errorCount: number;
  displayMessage: string;
}

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (info: { error: Error; errorInfo: { componentStack: string } }) => void;
  onReset?: () => void;
  errorMessage?: string;
  showRetry?: boolean;
  onRetry?: () => void;
  boundaryName?: string;
  componentName?: string;
}

export interface ErrorReport {
  error: Error;
  errorInfo: ErrorInfo;
  timestamp: string;
  boundaryName: string;
  userAgent: string;
  url: string;
  userId?: string;
  sessionId?: string;
}

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  severity?: ErrorSeverity;
  metadata?: Record<string, unknown>;
}

export enum BreadcrumbCategory {
  NAVIGATION = 'navigation',
  USER_ACTION = 'user.action',
  ERROR = 'error',
  STATE_CHANGE = 'state.change',
  API_CALL = 'api.call',
}
