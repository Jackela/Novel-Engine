/**
 * List of sensitive field names that should be redacted in logs
 * Case-insensitive matching using .includes() to catch variations
 * e.g., "password" matches "user_password", "passwordHash", etc.
 */
const SENSITIVE_KEYS = [
  'password',
  'apikey',
  'api_key',
  'secret',
  'authorization',
  'token',
  'accesstoken',
  'access_token',
  'refreshtoken',
  'refresh_token',
  'creditcard',
  'credit_card',
  'ssn',
  'cvv',
];

const REDACTED = '[REDACTED]';

/**
 * Sanitizer utility for removing PII and sensitive data from log entries
 * 
 * Features:
 * - Redacts sensitive field names (passwords, tokens, etc.)
 * - Partially masks email addresses (first 2 chars + domain)
 * - Handles circular references gracefully
 * - Recursively sanitizes nested objects and arrays
 * - Max depth protection to prevent stack overflow
 * 
 * Usage:
 *   const sanitized = Sanitizer.sanitize({ username: 'john', password: 'secret' });
 *   // Result: { username: 'john', password: '[REDACTED]' }
 */
export class Sanitizer {
  /**
   * Sanitize an object by removing or masking sensitive data
   * 
   * @param obj - Object to sanitize (can be any type)
   * @param maxDepth - Maximum recursion depth (default: 5)
   * @param seen - WeakSet for circular reference detection (internal use)
   * @returns Sanitized copy of the object
   */
  static sanitize(obj: unknown, maxDepth = 5, seen = new WeakSet()): unknown {
    // Handle non-object inputs
    if (obj === null || obj === undefined) {
      return obj;
    }

    if (typeof obj !== 'object') {
      return obj;
    }

    // Handle circular references
    if (seen.has(obj)) {
      return '[CIRCULAR]';
    }

    // Max depth protection
    if (maxDepth === 0) {
      return { '[MAX_DEPTH]': true };
    }

    // Mark this object as seen for circular reference detection
    seen.add(obj);

    // Handle arrays
    if (Array.isArray(obj)) {
      return obj.map((item) => this.sanitize(item, maxDepth - 1, seen));
    }

    // Handle objects
    const sanitized: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(obj)) {
      // Sanitize sensitive keys (case-insensitive)
      const lowerKey = key.toLowerCase();
      if (SENSITIVE_KEYS.some((sensitive) => lowerKey.includes(sensitive))) {
        sanitized[key] = REDACTED;
        continue;
      }

      // Sanitize email addresses (partial masking)
      if (lowerKey.includes('email') && typeof value === 'string') {
        const parts = value.split('@');
        if (parts.length === 2 && parts[0] && parts[1]) {
          const prefix = parts[0].substring(0, 2);
          sanitized[key] = `${prefix}**@${parts[1]}`;
        } else {
          sanitized[key] = value;
        }
        continue;
      }

      // Recursively sanitize nested objects and arrays
      if (typeof value === 'object' && value !== null) {
        sanitized[key] = this.sanitize(value, maxDepth - 1, seen);
      } else {
        sanitized[key] = value;
      }
    }

    return sanitized;
  }
}
