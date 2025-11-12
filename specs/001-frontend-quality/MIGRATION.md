# Migration Guide: console.log → Structured Logging

**Feature**: Frontend Quality Improvements  
**Date**: 2025-11-05  
**Status**: Complete

## Overview

This guide helps developers migrate from `console.log` statements to the structured logging system implemented in this feature. The logging service provides environment-aware log filtering, automatic PII sanitization, and structured context for easier debugging.

## Quick Reference

### Before and After

```typescript
// ❌ BEFORE: console.log
console.log('User login attempt');
console.log('Login failed:', error);
console.log('Character data:', characterData);

// ✅ AFTER: Structured logging
import { logger } from '@/services/logging/LoggerFactory';

logger.info('User login attempt', { component: 'AuthService', action: 'login' });
logger.error('Login failed', error as Error, { component: 'AuthService', action: 'login' });
logger.debug('Character data loaded', { component: 'CharacterService', characterId: characterData.id });
```

## Log Levels

### DEBUG (Development Only)
**Use for**: Detailed diagnostic information

```typescript
// Example: API request/response details
logger.debug(`API Request: ${method} ${url}`, {
  component: 'APIClient',
  action: 'request',
  method,
  url,
});
```

### INFO (Development Only)
**Use for**: General informational messages, user actions

```typescript
// Example: User actions
logger.info('Settings clicked', {
  component: 'Navbar',
  action: 'click',
  userId: currentUser.id,
});
```

### WARN (Development + Production)
**Use for**: Unexpected situations that don't prevent functionality

```typescript
// Example: Fallback to alternative approach
logger.warn(`Enhanced character data failed for ${name}, falling back: ${error.message}`);
```

### ERROR (Development + Production)
**Use for**: Error conditions requiring attention

```typescript
// Example: API errors
logger.error('Connection test failed:', error as Error, {
  component: 'NovelEngineAPI',
  action: 'testConnection',
});
```

## Common Patterns

### 1. Component Lifecycle Events

```typescript
// ❌ BEFORE
console.log('Dashboard mounted');
console.log('Dashboard state:', state);

// ✅ AFTER
const { info, debug } = useLogger('Dashboard');

useEffect(() => {
  info('Component mounted', { action: 'mount' });
  debug('Initial state loaded', { state });
}, []);
```

### 2. API Calls

```typescript
// ❌ BEFORE
console.log('Fetching characters...');
console.log('Characters loaded:', data);

// ✅ AFTER
logger.info('Fetching characters', { component: 'CharacterService', action: 'fetch' });
logger.debug('Characters loaded', { component: 'CharacterService', count: data.length });
```

### 3. Error Handling

```typescript
// ❌ BEFORE
try {
  await apiCall();
} catch (error) {
  console.error('API call failed:', error);
}

// ✅ AFTER
try {
  await apiCall();
} catch (error) {
  logger.error('API call failed', error as Error, {
    component: 'APIService',
    action: 'apiCall',
  });
}
```

### 4. User Actions

```typescript
// ❌ BEFORE
const handleSubmit = () => {
  console.log('Form submitted with data:', formData);
};

// ✅ AFTER
const { info } = useLogger('CharacterForm');

const handleSubmit = () => {
  info('Form submitted', {
    action: 'submit',
    characterId: formData.id,
    // formData will be sanitized automatically
  });
};
```

### 5. Sensitive Data (Automatic Sanitization)

```typescript
// ❌ BEFORE - Exposes password in logs
console.log('Login data:', { username, password });

// ✅ AFTER - Password automatically redacted
logger.debug('Login attempt', {
  component: 'LoginForm',
  action: 'submit',
  username, // Safe to log
  password, // Automatically becomes '[REDACTED]'
});
```

## React Component Migration

### Class Components

```typescript
import { logger } from '@/services/logging/LoggerFactory';

class MyComponent extends Component {
  componentDidMount() {
    logger.info('Component mounted', { component: 'MyComponent', action: 'mount' });
  }

  handleClick = () => {
    logger.debug('Button clicked', { component: 'MyComponent', action: 'click' });
  };
}
```

### Function Components with Hook

```typescript
import { useLogger } from '@/hooks/useLogger';

function MyComponent() {
  const { info, debug, warn, error } = useLogger('MyComponent');

  useEffect(() => {
    info('Component mounted', { action: 'mount' });
  }, [info]);

  const handleClick = () => {
    debug('Button clicked', { action: 'click' });
  };

  return <button onClick={handleClick}>Click me</button>;
}
```

## Service Migration

### API Service

```typescript
import { logger } from '@/services/logging/LoggerFactory';

class APIService {
  async fetchData() {
    try {
      logger.debug('Fetching data', { component: 'APIService', action: 'fetchData' });
      const response = await fetch('/api/data');
      logger.info('Data fetched successfully', { component: 'APIService', status: response.status });
      return response.json();
    } catch (error) {
      logger.error('Fetch failed', error as Error, { component: 'APIService', action: 'fetchData' });
      throw error;
    }
  }
}
```

### Authentication Service

```typescript
import { logger } from '@/services/logging/LoggerFactory';

class AuthService {
  async login(credentials: LoginRequest) {
    try {
      logger.info('Login attempt', { component: 'AuthService', action: 'login', username: credentials.username });
      const token = await this.apiClient.post('/auth/login', credentials);
      logger.info('Login successful', { component: 'AuthService', userId: token.user.id });
      return token;
    } catch (error) {
      logger.error('Login failed', error as Error, { component: 'AuthService', action: 'login' });
      throw error;
    }
  }
}
```

## Context Best Practices

### Required Fields

```typescript
{
  component: 'ComponentName',  // Always include
  action: 'actionName',        // Always include for user actions
}
```

### Optional Fields

```typescript
{
  userId: user.id,             // When available
  characterId: character.id,   // For character-specific actions
  errorCode: response.status,  // For API errors
  duration: elapsed,           // For performance tracking
}
```

### Avoid

```typescript
// ❌ Don't log sensitive data directly
logger.info('User credentials', { password: 'secret123' });

// ✅ Let sanitizer handle it
logger.debug('Login form data', formData); // password will be sanitized
```

## Production Behavior

### Automatic Filtering

In production (`NODE_ENV=production`):
- **DEBUG** logs: Not executed (zero overhead)
- **INFO** logs: Not executed (zero overhead)
- **WARN** logs: Logged to console and remote service
- **ERROR** logs: Logged to console and remote service

### Bundle Optimization

Terser configuration removes all `console.log` statements in production builds:

```typescript
// vite.config.ts
terserOptions: {
  compress: {
    drop_console: true, // Remove console.log in production
  },
}
```

## Testing with Logger

### Mock Logger in Tests

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { logger } from '@/services/logging/LoggerFactory';

describe('MyComponent', () => {
  beforeEach(() => {
    vi.spyOn(logger, 'info');
    vi.spyOn(logger, 'error');
  });

  it('logs component mount', () => {
    render(<MyComponent />);
    expect(logger.info).toHaveBeenCalledWith('Component mounted', expect.any(Object));
  });
});
```

### Test Sanitization

```typescript
import { Sanitizer } from '@/services/logging/Sanitizer';

it('sanitizes password in context', () => {
  const context = { username: 'john', password: 'secret' };
  const sanitized = Sanitizer.sanitize(context);
  
  expect(sanitized.password).toBe('[REDACTED]');
  expect(sanitized.username).toBe('john');
});
```

## Migration Checklist

- [ ] Identify all `console.log` statements in your code
- [ ] Replace with appropriate log level (debug, info, warn, error)
- [ ] Add structured context with `component` and `action`
- [ ] Use `useLogger` hook in React components
- [ ] Import logger singleton in services
- [ ] Test that sensitive data is sanitized
- [ ] Verify logs appear in development
- [ ] Verify production build has no console.log

## Performance Considerations

### Logger Overhead

- **Development**: ~5-10ms per log entry (negligible)
- **Production**: ~1-2ms for WARN/ERROR only
- **DEBUG/INFO**: Zero overhead in production (not executed)

### Best Practices

```typescript
// ✅ Good: Lightweight logging
logger.info('User action', { action: 'click' });

// ⚠️ Acceptable: Moderate data
logger.debug('API response', { status, headers });

// ❌ Avoid: Large objects in hot paths
for (let i = 0; i < 10000; i++) {
  logger.debug('Processing item', { item: largeObject }); // Performance hit
}
```

## Troubleshooting

### Logs not appearing in development

**Check**: Verify logger minimum level
```typescript
import { logger } from '@/services/logging/LoggerFactory';
console.log(logger.getMinLevel()); // Should be 'debug' in development
```

### Logs appearing in production

**Check**: Verify `NODE_ENV` is set to 'production'
```typescript
console.log(process.env.NODE_ENV); // Should be 'production'
```

### Sensitive data not sanitized

**Check**: Sanitizer sensitive keys list
```typescript
// Add custom sensitive keys
const SENSITIVE_KEYS = ['password', 'token', 'secret', 'apiKey', 'customSensitiveField'];
```

## Additional Resources

- **Logger Interface**: `frontend/src/services/logging/ILogger.ts`
- **Sanitizer**: `frontend/src/services/logging/Sanitizer.ts`
- **useLogger Hook**: `frontend/src/hooks/useLogger.ts`
- **Logger Tests**: `frontend/tests/unit/logging/`
- **Quickstart Guide**: `specs/001-frontend-quality/quickstart.md`
