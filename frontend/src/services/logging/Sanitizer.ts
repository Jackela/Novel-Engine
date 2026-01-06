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
const MAX_DEPTH_MARKER = { '[MAX_DEPTH]': true };

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const isSensitiveKey = (key: string): boolean => {
  const lowerKey = key.toLowerCase();
  return SENSITIVE_KEYS.some((sensitive) => lowerKey.includes(sensitive));
};

const isEmailKey = (key: string): boolean =>
  key.toLowerCase().includes('email');

const maskEmail = (value: string): string => {
  const parts = value.split('@');
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    return value;
  }
  const prefix = parts[0].substring(0, 2);
  return `${prefix}**@${parts[1]}`;
};

const sanitizeEntryValue = (
  key: string,
  value: unknown,
  maxDepth: number,
  seen: WeakSet<object>
): unknown => {
  if (isSensitiveKey(key)) {
    return REDACTED;
  }

  if (isEmailKey(key) && typeof value === 'string') {
    return maskEmail(value);
  }

  if (isRecord(value)) {
    return sanitizeValue(value, maxDepth - 1, seen);
  }

  return value;
};

const sanitizeObject = (
  obj: Record<string, unknown>,
  maxDepth: number,
  seen: WeakSet<object>
): Record<string, unknown> => {
  const sanitized: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    sanitized[key] = sanitizeEntryValue(key, value, maxDepth, seen);
  }

  return sanitized;
};

const sanitizeArray = (
  values: unknown[],
  maxDepth: number,
  seen: WeakSet<object>
): unknown[] => values.map((item) => sanitizeValue(item, maxDepth - 1, seen));

const sanitizeValue = (
  obj: unknown,
  maxDepth: number,
  seen: WeakSet<object>
): unknown => {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (!isRecord(obj)) {
    return obj;
  }

  if (seen.has(obj)) {
    return '[CIRCULAR]';
  }

  if (maxDepth === 0) {
    return MAX_DEPTH_MARKER;
  }

  seen.add(obj);

  if (Array.isArray(obj)) {
    return sanitizeArray(obj, maxDepth, seen);
  }

  return sanitizeObject(obj, maxDepth, seen);
};

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
    return sanitizeValue(obj, maxDepth, seen);
  }
}
