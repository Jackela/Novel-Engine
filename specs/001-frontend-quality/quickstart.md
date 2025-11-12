# Quickstart Guide: Frontend Quality Improvements

**Feature**: Frontend Quality Improvements  
**Branch**: `001-frontend-quality`  
**Date**: 2025-11-05

## Overview

This guide provides step-by-step instructions for implementing production-ready error handling, structured logging, complete authentication, and test coverage improvements in the React 18 frontend.

## Prerequisites

- Node.js 18+
- npm or yarn
- TypeScript 5.x
- React 18 knowledge
- Familiarity with Vite, Vitest, and Playwright

## Implementation Order (TDD Red-Green-Refactor)

Following Test-Driven Development (Article III), implement features in this order:

1. **Phase 1**: Logging Service (FR-007 to FR-014) - Foundation for all other features
2. **Phase 2**: Error Boundaries (FR-001 to FR-006) - Uses logging service
3. **Phase 3**: Authentication (FR-015 to FR-021) - Uses logging and error handling
4. **Phase 4**: Test Coverage (FR-027 to FR-033) - Test all implemented features
5. **Phase 5**: Type Safety (FR-034 to FR-036) - Final cleanup
6. **Phase 6**: WebSocket Decision (FR-022 to FR-026) - DEFERRED pending product decision

---

## Phase 1: Logging Service (Days 1-2)

### Step 1.1: Create Type Definitions

**File**: `frontend/src/types/logging.ts`

```typescript
export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
}

export interface LogContext {
  component?: string;
  action?: string;
  userId?: string;
  [key: string]: unknown;
}

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  timestamp: string;
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  context?: Record<string, unknown>;
  error?: {
    message: string;
    stack?: string;
    name: string;
  };
}

export interface LoggerConfig {
  minLevel: LogLevel;
  environment: 'development' | 'production';
  includeTimestamp: boolean;
  includeComponent: boolean;
  enableRemoteLogging: boolean;
  remoteUrl?: string;
}
```

### Step 1.2: Write Failing Tests (TDD Red)

**File**: `frontend/tests/unit/logging/Logger.test.ts`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { ConsoleLogger } from '../../../src/services/logging/ConsoleLogger';
import { LogLevel } from '../../../src/types/logging';

describe('ConsoleLogger', () => {
  it('should sanitize password in log context', () => {
    const logger = new ConsoleLogger();
    const context = { password: 'secret123', user: 'john' };
    const sanitized = logger.sanitize(context);
    
    expect(sanitized.password).toBe('***');
    expect(sanitized.user).toBe('john');
  });

  it('should not log DEBUG in production', () => {
    const logger = new ConsoleLogger({ 
      environment: 'production', 
      minLevel: LogLevel.WARN 
    });
    const spy = vi.spyOn(console, 'log');
    
    logger.debug('Debug message');
    
    expect(spy).not.toHaveBeenCalled();
  });

  it('should log ERROR in production', () => {
    const logger = new ConsoleLogger({ 
      environment: 'production', 
      minLevel: LogLevel.WARN 
    });
    const spy = vi.spyOn(console, 'error');
    
    logger.error('Error message');
    
    expect(spy).toHaveBeenCalled();
  });
});
```

**Run tests**: `npm test -- Logger.test.ts` → Tests fail (Red)

### Step 1.3: Implement Logger Interface (TDD Green)

**File**: `frontend/src/services/logging/ILogger.ts`

```typescript
import type { LogLevel, LogContext, LogEntry } from '../../types/logging';

export interface ILogger {
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, error?: Error, context?: LogContext): void;
  createLogEntry(level: LogLevel, message: string, context?: LogContext, error?: Error): LogEntry;
  sanitize(context: Record<string, unknown>): Record<string, unknown>;
  setMinLevel(level: LogLevel): void;
  getMinLevel(): LogLevel;
}
```

**File**: `frontend/src/services/logging/Sanitizer.ts`

```typescript
const SENSITIVE_KEYS = ['password', 'apiKey', 'secret', 'authorization', 'token', 'creditCard'];

export class Sanitizer {
  static sanitize(obj: Record<string, unknown>, maxDepth = 5): Record<string, unknown> {
    if (maxDepth === 0) return { '[MAX_DEPTH]': true };
    
    const sanitized: Record<string, unknown> = {};
    
    for (const [key, value] of Object.entries(obj)) {
      if (SENSITIVE_KEYS.includes(key.toLowerCase())) {
        sanitized[key] = '***';
      } else if (key.toLowerCase().includes('email') && typeof value === 'string') {
        sanitized[key] = value.substring(0, 2) + '**@' + value.split('@')[1];
      } else if (typeof value === 'object' && value !== null) {
        sanitized[key] = this.sanitize(value as Record<string, unknown>, maxDepth - 1);
      } else {
        sanitized[key] = value;
      }
    }
    
    return sanitized;
  }
}
```

**File**: `frontend/src/services/logging/ConsoleLogger.ts`

```typescript
import type { ILogger } from './ILogger';
import type { LogLevel, LogContext, LogEntry, LoggerConfig } from '../../types/logging';
import { Sanitizer } from './Sanitizer';

export class ConsoleLogger implements ILogger {
  private config: LoggerConfig;

  constructor(config?: Partial<LoggerConfig>) {
    this.config = {
      minLevel: config?.minLevel ?? LogLevel.DEBUG,
      environment: config?.environment ?? 'development',
      includeTimestamp: config?.includeTimestamp ?? true,
      includeComponent: config?.includeComponent ?? true,
      enableRemoteLogging: config?.enableRemoteLogging ?? false,
    };
  }

  debug(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.DEBUG)) {
      const entry = this.createLogEntry(LogLevel.DEBUG, message, context);
      console.log(`[DEBUG] ${entry.message}`, entry.context);
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.INFO)) {
      const entry = this.createLogEntry(LogLevel.INFO, message, context);
      console.info(`[INFO] ${entry.message}`, entry.context);
    }
  }

  warn(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.WARN)) {
      const entry = this.createLogEntry(LogLevel.WARN, message, context);
      console.warn(`[WARN] ${entry.message}`, entry.context);
    }
  }

  error(message: string, error?: Error, context?: LogContext): void {
    if (this.shouldLog(LogLevel.ERROR)) {
      const entry = this.createLogEntry(LogLevel.ERROR, message, context, error);
      console.error(`[ERROR] ${entry.message}`, entry.error, entry.context);
    }
  }

  createLogEntry(level: LogLevel, message: string, context?: LogContext, error?: Error): LogEntry {
    return {
      id: crypto.randomUUID(),
      level,
      message,
      timestamp: new Date().toISOString(),
      component: context?.component,
      action: context?.action,
      userId: context?.userId,
      sessionId: sessionStorage.getItem('sessionId') ?? undefined,
      context: context ? this.sanitize(context) : undefined,
      error: error ? {
        message: error.message,
        stack: this.config.environment === 'development' ? error.stack : undefined,
        name: error.name,
      } : undefined,
    };
  }

  sanitize(context: Record<string, unknown>): Record<string, unknown> {
    return Sanitizer.sanitize(context);
  }

  setMinLevel(level: LogLevel): void {
    this.config.minLevel = level;
  }

  getMinLevel(): LogLevel {
    return this.config.minLevel;
  }

  private shouldLog(level: LogLevel): boolean {
    const levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR];
    const minIndex = levels.indexOf(this.config.minLevel);
    const currentIndex = levels.indexOf(level);
    return currentIndex >= minIndex;
  }
}
```

**Run tests**: `npm test -- Logger.test.ts` → Tests pass (Green)

### Step 1.4: Create Logger Factory

**File**: `frontend/src/services/logging/LoggerFactory.ts`

```typescript
import type { ILogger } from './ILogger';
import { ConsoleLogger } from './ConsoleLogger';
import { LogLevel } from '../../types/logging';

export class LoggerFactory {
  static create(): ILogger {
    const environment = import.meta.env.PROD ? 'production' : 'development';
    const minLevel = import.meta.env.PROD ? LogLevel.WARN : LogLevel.DEBUG;
    
    return new ConsoleLogger({ environment, minLevel });
  }
}

// Global logger instance
export const logger = LoggerFactory.create();
```

### Step 1.5: Create React Hook for Logger

**File**: `frontend/src/hooks/useLogger.ts`

```typescript
import { useCallback, useMemo } from 'react';
import { logger } from '../services/logging/LoggerFactory';
import type { LogContext } from '../types/logging';

export function useLogger(componentName?: string) {
  const baseContext: LogContext = useMemo(
    () => ({ component: componentName }),
    [componentName]
  );

  const debug = useCallback(
    (message: string, context?: LogContext) => {
      logger.debug(message, { ...baseContext, ...context });
    },
    [baseContext]
  );

  const info = useCallback(
    (message: string, context?: LogContext) => {
      logger.info(message, { ...baseContext, ...context });
    },
    [baseContext]
  );

  const warn = useCallback(
    (message: string, context?: LogContext) => {
      logger.warn(message, { ...baseContext, ...context });
    },
    [baseContext]
  );

  const error = useCallback(
    (message: string, err?: Error, context?: LogContext) => {
      logger.error(message, err, { ...baseContext, ...context });
    },
    [baseContext]
  );

  return { debug, info, warn, error };
}
```

### Step 1.6: Replace console.log Statements

**Strategy**: Incremental replacement across codebase

```bash
# Find all console.log statements
grep -r "console\\.log" frontend/src --include="*.ts" --include="*.tsx" | wc -l
# Result: ~265 files

# Replace in batches by directory:
# 1. components/admin/ (knowledge management already fixed)
# 2. components/character/
# 3. components/story/
# 4. hooks/
# 5. services/

# Example replacement:
# BEFORE:
console.log('[KnowledgeAPI] Failed to create entry:', error);

# AFTER:
import { logger } from '@/services/logging/LoggerFactory';
logger.error('Failed to create entry', error, { component: 'KnowledgeAPI', action: 'createEntry' });
```

---

## Phase 2: Error Boundaries (Days 3-4)

### Step 2.1: Write Failing Tests (TDD Red)

**File**: `frontend/tests/unit/error-boundaries/ErrorBoundary.test.tsx`

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../../../src/components/error-boundaries/ErrorBoundary';

describe('ErrorBoundary', () => {
  it('should render children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('should display fallback UI when child throws error', () => {
    const ThrowError = () => {
      throw new Error('Test error');
    };
    
    render(
      <ErrorBoundary fallback={<div>Error occurred</div>}>
        <ThrowError />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Error occurred')).toBeInTheDocument();
  });

  it('should call onError callback when error occurs', () => {
    const onError = vi.fn();
    const ThrowError = () => {
      throw new Error('Test error');
    };
    
    render(
      <ErrorBoundary onError={onError}>
        <ThrowError />
      </ErrorBoundary>
    );
    
    expect(onError).toHaveBeenCalled();
  });
});
```

**Run tests**: `npm test -- ErrorBoundary.test.tsx` → Tests fail (Red)

### Step 2.2: Implement Error Boundary (TDD Green)

**File**: `frontend/src/components/error-boundaries/ErrorBoundary.tsx`

```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { logger } from '../../services/logging/LoggerFactory';

interface Props {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, errorInfo: ErrorInfo) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  errorMessage?: string;
  showRetry?: boolean;
  onRetry?: () => void;
  boundaryName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundaryCore extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });
    
    // Log error
    logger.error('Error boundary caught error', error, {
      component: this.props.boundaryName || 'ErrorBoundary',
      action: 'componentDidCatch',
      errorInfo: errorInfo.componentStack,
    });
    
    // Call onError callback
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    this.props.onRetry?.();
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      // Custom fallback
      if (this.props.fallback) {
        if (typeof this.props.fallback === 'function') {
          return this.props.fallback(this.state.error, this.state.errorInfo!);
        }
        return this.props.fallback;
      }
      
      // Default fallback UI
      return (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h2>Something went wrong</h2>
          <p>{this.props.errorMessage || 'An unexpected error occurred'}</p>
          {this.props.showRetry && (
            <button onClick={this.handleRetry}>Try Again</button>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// Functional wrapper for cleaner API
export const ErrorBoundary: React.FC<Props> = (props) => (
  <ErrorBoundaryCore {...props} />
);
```

**Run tests**: `npm test -- ErrorBoundary.test.tsx` → Tests pass (Green)

### Step 2.3: Create Route-Level Error Boundaries

**File**: `frontend/src/components/error-boundaries/RouteErrorBoundary.tsx`

```typescript
import { ErrorBoundary } from './ErrorBoundary';
import { useNavigate } from 'react-router-dom';

export const RouteErrorBoundary: React.FC<{ children: React.ReactNode; routeName: string }> = ({
  children,
  routeName,
}) => {
  const navigate = useNavigate();

  return (
    <ErrorBoundary
      boundaryName={`Route-${routeName}`}
      errorMessage="This page encountered an error. You can try again or go home."
      showRetry
      onRetry={() => window.location.reload()}
      fallback={(error) => (
        <div style={{ padding: '40px', textAlign: 'center' }}>
          <h1>Oops! Something went wrong</h1>
          <p>We're sorry, but this page encountered an error.</p>
          <div style={{ marginTop: '20px' }}>
            <button onClick={() => window.location.reload()} style={{ marginRight: '10px' }}>
              Try Again
            </button>
            <button onClick={() => navigate('/')}>Go Home</button>
          </div>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
};
```

### Step 2.4: Integrate Error Boundaries in App

**File**: `frontend/src/App.tsx` (add root error boundary)

```typescript
import { ErrorBoundary } from './components/error-boundaries/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary boundaryName="RootErrorBoundary">
      {/* Existing app content */}
    </ErrorBoundary>
  );
}
```

**File**: `frontend/src/pages/Dashboard.tsx` (add route error boundary)

```typescript
import { RouteErrorBoundary } from '../components/error-boundaries/RouteErrorBoundary';

export function Dashboard() {
  return (
    <RouteErrorBoundary routeName="Dashboard">
      {/* Dashboard content */}
    </RouteErrorBoundary>
  );
}
```

---

## Phase 3: Authentication (Days 5-6)

### Step 3.1: Write Failing Auth Tests (TDD Red)

**File**: `frontend/tests/unit/auth/JWTAuthService.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JWTAuthService } from '../../../src/services/auth/JWTAuthService';

describe('JWTAuthService', () => {
  let authService: JWTAuthService;

  beforeEach(() => {
    authService = new JWTAuthService({
      apiBaseUrl: 'http://localhost:8000',
      tokenStorage: mockTokenStorage,
    });
  });

  it('should login with valid credentials', async () => {
    const token = await authService.login({
      username: 'test_user',
      password: 'password123',
    });
    
    expect(token).toHaveProperty('accessToken');
    expect(token).toHaveProperty('refreshToken');
  });

  it('should refresh token before expiration', async () => {
    // Test token refresh logic
  });

  it('should logout and clear token', async () => {
    await authService.logout();
    expect(authService.isAuthenticated()).toBe(false);
  });
});
```

### Step 3.2: Implement Authentication Service (TDD Green)

**File**: `frontend/src/services/auth/JWTAuthService.ts`

```typescript
import type { IAuthenticationService } from './IAuthenticationService';
import type { AuthToken, LoginRequest, AuthState } from '../../types/auth';
import { apiClient } from '../api/apiClient';
import { logger } from '../logging/LoggerFactory';

export class JWTAuthService implements IAuthenticationService {
  private token: AuthToken | null = null;
  private authState: AuthState = {
    isAuthenticated: false,
    token: null,
    isRefreshing: false,
    lastError: null,
    lastLoginAt: null,
    isInitialized: false,
  };
  private listeners: Array<(state: AuthState) => void> = [];

  async login(request: LoginRequest): Promise<AuthToken> {
    try {
      const response = await apiClient.post('/api/v1/auth/login', {
        username: request.username,
        password: request.password,
      });
      
      const token: AuthToken = {
        accessToken: response.data.access_token,
        refreshToken: response.data.refresh_token,
        tokenType: response.data.token_type,
        expiresAt: Date.now() + response.data.expires_in * 1000,
        refreshExpiresAt: Date.now() + (response.data.refresh_expires_in || 7 * 24 * 60 * 60) * 1000,
        user: response.data.user,
      };
      
      this.setToken(token);
      logger.info('User logged in successfully', { component: 'JWTAuthService', userId: token.user.id });
      
      return token;
    } catch (error) {
      logger.error('Login failed', error as Error, { component: 'JWTAuthService' });
      throw new Error('Login failed');
    }
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } finally {
      this.clearToken();
      logger.info('User logged out', { component: 'JWTAuthService' });
    }
  }

  async refreshToken(): Promise<AuthToken> {
    if (!this.token?.refreshToken) {
      throw new Error('No refresh token available');
    }
    
    this.updateAuthState({ isRefreshing: true });
    
    try {
      const response = await apiClient.post('/api/v1/auth/refresh', {
        refresh_token: this.token.refreshToken,
      });
      
      const newToken: AuthToken = {
        ...this.token,
        accessToken: response.data.access_token,
        expiresAt: Date.now() + response.data.expires_in * 1000,
      };
      
      this.setToken(newToken);
      logger.info('Token refreshed successfully', { component: 'JWTAuthService' });
      
      return newToken;
    } catch (error) {
      logger.error('Token refresh failed', error as Error, { component: 'JWTAuthService' });
      this.clearToken();
      throw new Error('Token refresh failed');
    } finally {
      this.updateAuthState({ isRefreshing: false });
    }
  }

  getToken(): AuthToken | null {
    return this.token;
  }

  isAuthenticated(): boolean {
    return this.token !== null && !this.isTokenExpired();
  }

  isTokenExpired(token?: AuthToken | null, bufferSeconds = 300): boolean {
    const t = token ?? this.token;
    if (!t) return true;
    
    const now = Date.now();
    const expiresAt = t.expiresAt - bufferSeconds * 1000;
    return now >= expiresAt;
  }

  getAuthState(): AuthState {
    return { ...this.authState };
  }

  onAuthStateChange(callback: (state: AuthState) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  async initialize(): Promise<void> {
    // Check for existing token in storage
    // Validate token
    // Set initial auth state
    this.updateAuthState({ isInitialized: true });
  }

  setToken(token: AuthToken): void {
    this.token = token;
    this.updateAuthState({
      isAuthenticated: true,
      token,
      lastLoginAt: new Date().toISOString(),
      lastError: null,
    });
  }

  clearToken(): void {
    this.token = null;
    this.updateAuthState({
      isAuthenticated: false,
      token: null,
      lastError: null,
    });
  }

  private updateAuthState(updates: Partial<AuthState>): void {
    this.authState = { ...this.authState, ...updates };
    this.listeners.forEach((listener) => listener(this.authState));
  }
}
```

---

## Testing Strategy

### Unit Tests (75%)

Target: Core logic, pure functions, services

```bash
# Run unit tests
npm test -- --coverage

# Coverage thresholds (vitest.config.ts)
coverage: {
  lines: 60,
  functions: 60,
  branches: 60,
  statements: 60,
  thresholds: {
    perFile: true,
    lines: 60,
  },
}
```

### Integration Tests (20%)

Target: Redux store, React Query, API integration

```typescript
// Example: Auth flow integration test
describe('Auth Flow Integration', () => {
  it('should login, make authenticated request, and logout', async () => {
    const authService = new JWTAuthService(config);
    
    // Login
    await authService.login({ username: 'test', password: 'pass' });
    expect(authService.isAuthenticated()).toBe(true);
    
    // Make authenticated request
    const response = await apiClient.get('/api/v1/protected');
    expect(response.status).toBe(200);
    
    // Logout
    await authService.logout();
    expect(authService.isAuthenticated()).toBe(false);
  });
});
```

### E2E Tests (5%)

Target: Critical user journeys

```typescript
// Playwright E2E test
test('user can login and view dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="username"]', 'test_user');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('h1')).toContainText('Dashboard');
});
```

---

## Verification Checklist

### Success Criteria Verification

- [ ] **SC-001**: Zero console.log in production build (`npm run build:prod` → check bundle)
- [ ] **SC-002**: Error boundaries prevent crashes (trigger error → verify fallback UI)
- [ ] **SC-003**: Auth enforced in all envs (check no bypasses in code review)
- [ ] **SC-004**: 60%+ test coverage (`npm run test:coverage` → check report)
- [ ] **SC-005**: Bundle size <50KB increase (`npm run build` → compare sizes)
- [ ] **SC-007**: Logging sanitizes PII (test with sensitive data → check logs)
- [ ] **SC-008**: <10 'any' types (`npm run type-check` → verify)

### Manual Testing

1. **Error Boundaries**: Trigger error in Dashboard → verify fallback + logging
2. **Logging**: Check browser console in dev → verify structured logs
3. **Auth**: Login → verify token → make API call → verify auth header → logout
4. **Production Build**: `npm run build:prod` → verify no console.log in bundle

---

## Troubleshooting

### Issue: Tests timeout
**Solution**: Check test cleanup, close WebSocket connections, clear timers

### Issue: Logging service performance
**Solution**: Profile logger with Chrome DevTools, ensure <100ms overhead

### Issue: Auth token not persisting
**Solution**: Check tokenStorage implementation, verify httpOnly cookie setup

### Issue: Error boundary not catching error
**Solution**: Verify error thrown during render, check error boundary placement

---

## Next Steps

After completing this quickstart:

1. Run `/speckit.tasks` to generate detailed task breakdown
2. Implement features following TDD Red-Green-Refactor cycle
3. Verify success criteria after each phase
4. Update documentation as implementation progresses
5. Create PR with comprehensive testing evidence

## Resources

- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Vitest Coverage](https://vitest.dev/guide/coverage.html)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [Playwright Testing](https://playwright.dev/docs/intro)
- [TypeScript Type Guards](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
