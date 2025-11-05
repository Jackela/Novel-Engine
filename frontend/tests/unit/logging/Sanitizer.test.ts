/**
 * Sanitizer Unit Tests
 * 
 * Test suite for PII/sensitive data sanitization utility following TDD Red-Green-Refactor cycle
 * 
 * Constitution Compliance:
 * - Article III (TDD): Tests written BEFORE implementation
 * - Article VII (Observability): Verify sensitive data protection in logs
 * - Article V (SOLID): SRP - Sanitizer only handles data sanitization
 */

import { describe, it, expect } from 'vitest';
import { Sanitizer } from '../../../src/services/logging/Sanitizer';

describe('Sanitizer', () => {
  describe('Basic Sanitization', () => {
    it('should sanitize password field', () => {
      const input = { username: 'john', password: 'secret123' };
      const result = Sanitizer.sanitize(input);

      expect(result.username).toBe('john');
      expect(result.password).toBe('[REDACTED]');
    });

    it('should sanitize token field', () => {
      const input = { action: 'login', token: 'Bearer abc123' };
      const result = Sanitizer.sanitize(input);

      expect(result.action).toBe('login');
      expect(result.token).toBe('[REDACTED]');
    });

    it('should sanitize apiKey field', () => {
      const input = { service: 'api', apiKey: 'sk-123456' };
      const result = Sanitizer.sanitize(input);

      expect(result.service).toBe('api');
      expect(result.apiKey).toBe('[REDACTED]');
    });

    it('should sanitize secret field', () => {
      const input = { config: 'test', secret: 'mysecret' };
      const result = Sanitizer.sanitize(input);

      expect(result.config).toBe('test');
      expect(result.secret).toBe('[REDACTED]');
    });
  });

  // T029: Test for log sanitization with nested objects
  describe('Nested Object Sanitization', () => {
    it('should sanitize nested objects with sensitive fields', () => {
      const input = {
        user: {
          username: 'john',
          password: 'secret123',
        },
        metadata: {
          timestamp: Date.now(),
        },
      };

      const result = Sanitizer.sanitize(input);

      expect(result.user.username).toBe('john');
      expect(result.user.password).toBe('[REDACTED]');
      expect(result.metadata.timestamp).toBeDefined();
    });

    it('should sanitize deeply nested objects', () => {
      const input = {
        level1: {
          level2: {
            level3: {
              username: 'test',
              token: 'Bearer xyz',
            },
          },
        },
      };

      const result = Sanitizer.sanitize(input);

      expect(result.level1.level2.level3.username).toBe('test');
      expect(result.level1.level2.level3.token).toBe('[REDACTED]');
    });

    it('should sanitize arrays of objects', () => {
      const input = {
        users: [
          { username: 'user1', password: 'pass1' },
          { username: 'user2', apiKey: 'key2' },
        ],
      };

      const result = Sanitizer.sanitize(input);

      expect(result.users[0].username).toBe('user1');
      expect(result.users[0].password).toBe('[REDACTED]');
      expect(result.users[1].username).toBe('user2');
      expect(result.users[1].apiKey).toBe('[REDACTED]');
    });

    it('should handle mixed nested structures', () => {
      const input = {
        request: {
          headers: {
            authorization: 'Bearer token123',
            'content-type': 'application/json',
          },
          body: {
            username: 'john',
            password: 'secret',
            data: {
              items: [
                { id: 1, secret: 'key1' },
                { id: 2, value: 'safe' },
              ],
            },
          },
        },
      };

      // Use higher maxDepth for deeply nested structure (6 levels deep)
      const result = Sanitizer.sanitize(input, 10);

      expect(result.request.headers.authorization).toBe('[REDACTED]');
      expect(result.request.headers['content-type']).toBe('application/json');
      expect(result.request.body.username).toBe('john');
      expect(result.request.body.password).toBe('[REDACTED]');
      expect(result.request.body.data.items[0].id).toBe(1);
      expect(result.request.body.data.items[0].secret).toBe('[REDACTED]');
      expect(result.request.body.data.items[1].id).toBe(2);
      expect(result.request.body.data.items[1].value).toBe('safe');
    });
  });

  describe('Case Insensitive Sanitization', () => {
    it('should sanitize fields regardless of case', () => {
      const input = {
        Password: 'test1',
        TOKEN: 'test2',
        ApiKey: 'test3',
        SECRET: 'test4',
      };

      const result = Sanitizer.sanitize(input);

      expect(result.Password).toBe('[REDACTED]');
      expect(result.TOKEN).toBe('[REDACTED]');
      expect(result.ApiKey).toBe('[REDACTED]');
      expect(result.SECRET).toBe('[REDACTED]');
    });
  });

  describe('Authorization Header Sanitization', () => {
    it('should sanitize Authorization header', () => {
      const input = {
        headers: {
          Authorization: 'Bearer token123',
          'X-Custom-Header': 'safe-value',
        },
      };

      const result = Sanitizer.sanitize(input);

      expect(result.headers.Authorization).toBe('[REDACTED]');
      expect(result.headers['X-Custom-Header']).toBe('safe-value');
    });

    it('should sanitize authorization header (lowercase)', () => {
      const input = {
        headers: {
          authorization: 'Bearer token123',
        },
      };

      const result = Sanitizer.sanitize(input);

      expect(result.headers.authorization).toBe('[REDACTED]');
    });
  });

  describe('Edge Cases', () => {
    it('should handle null values', () => {
      const input = { username: 'john', password: null };
      const result = Sanitizer.sanitize(input);

      expect(result.username).toBe('john');
      expect(result.password).toBe('[REDACTED]');
    });

    it('should handle undefined values', () => {
      const input = { username: 'john', token: undefined };
      const result = Sanitizer.sanitize(input);

      expect(result.username).toBe('john');
      expect(result.token).toBe('[REDACTED]');
    });

    it('should handle empty objects', () => {
      const input = {};
      const result = Sanitizer.sanitize(input);

      expect(result).toEqual({});
    });

    it('should handle non-object inputs', () => {
      expect(Sanitizer.sanitize('string')).toBe('string');
      expect(Sanitizer.sanitize(123)).toBe(123);
      expect(Sanitizer.sanitize(true)).toBe(true);
      expect(Sanitizer.sanitize(null)).toBe(null);
    });

    it('should handle circular references without infinite loop', () => {
      const input: any = { name: 'test', password: 'secret' };
      input.self = input; // Circular reference

      const result = Sanitizer.sanitize(input);

      expect(result.name).toBe('test');
      expect(result.password).toBe('[REDACTED]');
      // Should handle circular reference gracefully
    });
  });

  describe('Non-Sensitive Data Preservation', () => {
    it('should preserve non-sensitive fields unchanged (email gets partial masking)', () => {
      const input = {
        id: 123,
        name: 'John Doe',
        email: 'john@example.com',
        metadata: {
          timestamp: 1234567890,
          source: 'api',
        },
      };

      const result = Sanitizer.sanitize(input);

      expect(result.id).toBe(123);
      expect(result.name).toBe('John Doe');
      expect(result.email).toBe('jo**@example.com'); // Partial masking applied
      expect(result.metadata).toEqual({ timestamp: 1234567890, source: 'api' });
    });
  });
});
