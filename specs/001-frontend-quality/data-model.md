# Data Models: Frontend Quality Improvements

**Feature**: Frontend Quality Improvements  
**Branch**: `001-frontend-quality`  
**Date**: 2025-11-05

## Overview

This document defines the data models, state shapes, and type definitions for error handling, logging, authentication, and related infrastructure components. All models follow TypeScript strict mode conventions and support the ports & adapters architecture.

## 1. Error Boundary Models

### ErrorBoundaryState

Represents the state of an error boundary component.

```typescript
interface ErrorBoundaryState {
  /** Whether an error has occurred */
  hasError: boolean;
  
  /** The error object (if hasError is true) */
  error: Error | null;
  
  /** React error info with component stack */
  errorInfo: React.ErrorInfo | null;
  
  /** Timestamp when error occurred (ISO 8601) */
  errorTimestamp: string | null;
  
  /** Number of errors caught by this boundary */
  errorCount: number;
  
  /** User-friendly error message for display */
  displayMessage: string;
}
```

**Validation Rules**:
- `hasError` must be `true` if `error` is not `null`
- `errorTimestamp` must be valid ISO 8601 format
- `displayMessage` must not contain stack traces or sensitive info
- `errorCount` must be non-negative

**State Transitions**:
```
Initial State → Error Caught → Error Cleared → Initial State
   (no error)     (hasError=true)  (reset)     (hasError=false)
```

### ErrorBoundaryProps

Props for configuring error boundary behavior.

```typescript
interface ErrorBoundaryProps {
  /** Child components to protect */
  children: React.ReactNode;
  
  /** Fallback UI when error occurs (optional) */
  fallback?: React.ReactNode | ((error: Error, errorInfo: React.ErrorInfo) => React.ReactNode);
  
  /** Callback when error occurs (for logging/reporting) */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  
  /** Custom error message for users */
  errorMessage?: string;
  
  /** Whether to show "Try Again" button */
  showRetry?: boolean;
  
  /** Callback for retry action */
  onRetry?: () => void;
  
  /** Error boundary name for logging context */
  boundaryName?: string;
}
```

---

## 2. Logging Models

### LogLevel

Enum for log severity levels.

```typescript
enum LogLevel {
  DEBUG = 'debug',   // Development only, auto-removed in production
  INFO = 'info',     // Development only, auto-removed in production
  WARN = 'warn',     // Both environments, indicates potential issues
  ERROR = 'error',   // Both environments, indicates failures
}
```

**Environment Filtering**:
- Development: All levels (DEBUG, INFO, WARN, ERROR)
- Production: WARN and ERROR only (DEBUG/INFO dropped by Terser)

### LogEntry

Represents a single log event with structured context.

```typescript
interface LogEntry {
  /** Unique log entry ID */
  id: string;
  
  /** Log severity level */
  level: LogLevel;
  
  /** Log message (human-readable) */
  message: string;
  
  /** Timestamp (ISO 8601) */
  timestamp: string;
  
  /** Component or module that created log */
  component?: string;
  
  /** User action that triggered log */
  action?: string;
  
  /** Current user ID (if authenticated) */
  userId?: string;
  
  /** Session ID for request correlation */
  sessionId?: string;
  
  /** Additional structured context (sanitized) */
  context?: Record<string, unknown>;
  
  /** Error object (if level is ERROR) */
  error?: {
    message: string;
    stack?: string;
    name: string;
  };
}
```

**Validation Rules**:
- `level` must be valid LogLevel enum value
- `timestamp` must be ISO 8601 format
- `message` must be non-empty
- `context` must not contain sensitive data (sanitized)
- `error.stack` only included in development environment

### LogContext

Context data passed to logging methods.

```typescript
interface LogContext {
  /** Component or module name */
  component?: string;
  
  /** User action description */
  action?: string;
  
  /** User ID (sanitized) */
  userId?: string;
  
  /** Additional metadata (will be sanitized) */
  [key: string]: unknown;
}
```

### SanitizationRules

Configuration for automatic data sanitization.

```typescript
interface SanitizationRules {
  /** Property names to remove entirely */
  removeKeys: string[];
  
  /** Property names to mask (show partial) */
  maskKeys: string[];
  
  /** Regex patterns to detect sensitive data */
  patterns: {
    email: RegExp;
    token: RegExp;
    creditCard: RegExp;
    ssn: RegExp;
  };
  
  /** Max depth for nested object sanitization */
  maxDepth: number;
}

// Default rules
const DEFAULT_SANITIZATION_RULES: SanitizationRules = {
  removeKeys: [
    'password',
    'apiKey',
    'secret',
    'authorization',
    'creditCard',
    'cvv',
    'ssn',
  ],
  maskKeys: [
    'email',
    'token',
    'accessToken',
    'refreshToken',
  ],
  patterns: {
    email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    token: /^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/,
    creditCard: /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g,
    ssn: /\b\d{3}-\d{2}-\d{4}\b/g,
  },
  maxDepth: 5,
};
```

---

## 3. Authentication Models

### AuthToken

Represents authentication credentials.

```typescript
interface AuthToken {
  /** JWT access token */
  accessToken: string;
  
  /** JWT refresh token (for token renewal) */
  refreshToken: string;
  
  /** Token type (usually "Bearer") */
  tokenType: string;
  
  /** Access token expiration timestamp (Unix epoch) */
  expiresAt: number;
  
  /** Refresh token expiration timestamp (Unix epoch) */
  refreshExpiresAt: number;
  
  /** User identity extracted from token */
  user: {
    id: string;
    username: string;
    email: string;
    roles: string[];
  };
}
```

**Validation Rules**:
- `accessToken` must be non-empty string
- `expiresAt` must be future timestamp
- `refreshExpiresAt` must be > `expiresAt`
- `user.id` must be non-empty
- Tokens must be stored in httpOnly cookies (if available) or sessionStorage

**Token Lifecycle**:
```
Login → Token Issued → Token Refreshed → Token Expired → Re-login
       (expiresAt)    (5 min before)    (refreshExpiresAt)
```

### AuthState

Represents current authentication state in application.

```typescript
interface AuthState {
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  
  /** Current auth token (null if not authenticated) */
  token: AuthToken | null;
  
  /** Whether token refresh is in progress */
  isRefreshing: boolean;
  
  /** Last authentication error (if any) */
  lastError: string | null;
  
  /** Timestamp of last successful login */
  lastLoginAt: string | null;
  
  /** Whether initial auth check is complete */
  isInitialized: boolean;
}
```

**State Transitions**:
```
Uninitialized → Initializing → Authenticated → Refreshing → Authenticated
                             ↓                            ↓
                          Unauthenticated ← Expired ← Refresh Failed
```

### LoginRequest

Login credentials submitted by user.

```typescript
interface LoginRequest {
  /** Username or email */
  username: string;
  
  /** Password (never logged, always sanitized) */
  password: string;
  
  /** Optional: Remember me flag */
  rememberMe?: boolean;
}
```

**Validation Rules**:
- `username` must be non-empty, 3-50 characters
- `password` must be non-empty, 8-100 characters
- NEVER log `password` field (auto-sanitized by logger)

### LoginResponse

Backend response to successful login.

```typescript
interface LoginResponse {
  /** Access token */
  access_token: string;
  
  /** Refresh token */
  refresh_token: string;
  
  /** Token type (e.g., "Bearer") */
  token_type: string;
  
  /** Expiration time in seconds */
  expires_in: number;
  
  /** User information */
  user: {
    id: string;
    username: string;
    email: string;
    roles: string[];
  };
}
```

---

## 4. Error Reporting Models

### ErrorReport

Structured error report sent to error tracking service.

```typescript
interface ErrorReport {
  /** Error message */
  message: string;
  
  /** Error stack trace (sanitized) */
  stack?: string;
  
  /** Error name/type */
  name: string;
  
  /** Severity level */
  severity: 'fatal' | 'error' | 'warning' | 'info';
  
  /** Where error occurred */
  context: {
    /** Component or module */
    component?: string;
    
    /** User action */
    action?: string;
    
    /** Route/path where error occurred */
    route?: string;
    
    /** User ID (anonymized) */
    userId?: string;
    
    /** Browser info */
    browser?: {
      name: string;
      version: string;
      os: string;
    };
    
    /** Additional metadata (sanitized) */
    extra?: Record<string, unknown>;
  };
  
  /** Timestamp (ISO 8601) */
  timestamp: string;
  
  /** Error fingerprint for deduplication */
  fingerprint?: string[];
}
```

**Validation Rules**:
- `message` must be non-empty
- `severity` must be valid enum value
- `context.extra` must be sanitized (no PII/tokens)
- `stack` should be trimmed to max 50 lines
- `fingerprint` used for grouping similar errors

---

## 5. Test-Related Models

### TestCleanupRegistry

Registry for test resource cleanup.

```typescript
interface TestCleanupRegistry {
  /** Registered cleanup functions */
  cleanupFunctions: Array<() => Promise<void> | void>;
  
  /** Register a cleanup function */
  register(fn: () => Promise<void> | void): void;
  
  /** Run all cleanup functions */
  runAll(): Promise<void>;
  
  /** Clear registry */
  clear(): void;
}
```

**Usage in Tests**:
```typescript
// test/utils/cleanup.ts
const registry: TestCleanupRegistry = {
  cleanupFunctions: [],
  register(fn) { this.cleanupFunctions.push(fn); },
  async runAll() {
    for (const fn of this.cleanupFunctions.splice(0)) {
      await fn();
    }
  },
  clear() { this.cleanupFunctions = []; },
};

// vitest.setup.ts
afterEach(async () => { await registry.runAll(); });
```

---

## 6. Configuration Models

### LoggerConfig

Configuration for logging service.

```typescript
interface LoggerConfig {
  /** Minimum log level to output */
  minLevel: LogLevel;
  
  /** Whether to include timestamps */
  includeTimestamp: boolean;
  
  /** Whether to include component names */
  includeComponent: boolean;
  
  /** Sanitization rules */
  sanitization: SanitizationRules;
  
  /** Environment (dev/prod) */
  environment: 'development' | 'production';
  
  /** Whether to send to remote service */
  enableRemoteLogging: boolean;
  
  /** Remote service URL (if enabled) */
  remoteUrl?: string;
}
```

### ErrorBoundaryConfig

Global error boundary configuration.

```typescript
interface ErrorBoundaryConfig {
  /** Default error message for users */
  defaultMessage: string;
  
  /** Whether to show stack traces in dev */
  showStackInDev: boolean;
  
  /** Whether to enable retry buttons */
  enableRetry: boolean;
  
  /** Max errors before disabling boundary */
  maxErrors: number;
  
  /** Error reporting service */
  reporter?: IErrorReporter;
}
```

---

## Model Relationships

```
ErrorBoundary ──┬─► ErrorBoundaryState
                └─► ErrorBoundaryProps ──► onError() ──► ILogger
                                                      ├─► IErrorReporter
                                                      └─► ErrorReport

ILogger ──┬─► LogEntry ──┬─► LogLevel
          │              └─► LogContext ──► SanitizationRules
          └─► LoggerConfig

IAuthenticationService ──┬─► AuthToken ──► AuthState
                        ├─► LoginRequest
                        └─► LoginResponse

TestCleanupRegistry ──► afterEach/afterAll hooks
```

## Type Export Structure

```typescript
// frontend/src/types/logging.ts
export {
  LogLevel,
  LogEntry,
  LogContext,
  LoggerConfig,
  SanitizationRules,
};

// frontend/src/types/auth.ts
export {
  AuthToken,
  AuthState,
  LoginRequest,
  LoginResponse,
};

// frontend/src/types/errors.ts
export {
  ErrorBoundaryState,
  ErrorBoundaryProps,
  ErrorBoundaryConfig,
  ErrorReport,
};

// frontend/src/types/testing.ts
export {
  TestCleanupRegistry,
};
```

## Validation Functions

```typescript
// Type guards for runtime validation
function isLogLevel(value: unknown): value is LogLevel {
  return typeof value === 'string' && Object.values(LogLevel).includes(value as LogLevel);
}

function isAuthToken(value: unknown): value is AuthToken {
  return (
    value !== null &&
    typeof value === 'object' &&
    'accessToken' in value &&
    'refreshToken' in value &&
    'expiresAt' in value
  );
}

function isErrorReport(value: unknown): value is ErrorReport {
  return (
    value !== null &&
    typeof value === 'object' &&
    'message' in value &&
    'severity' in value &&
    'timestamp' in value
  );
}
```

---

## Summary

This data model design supports:
- ✅ Ports & Adapters architecture (interface-based)
- ✅ Type safety with TypeScript strict mode
- ✅ Runtime validation with type guards
- ✅ Clear state transitions
- ✅ Automatic sanitization for security
- ✅ Test-friendly design with cleanup registry
- ✅ Observable state for debugging
- ✅ Constitution compliance (Article II, IV, V)
