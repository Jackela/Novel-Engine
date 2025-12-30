/**
 * Magic UI Utilities
 * ==================
 * 
 * Core utility functions for Magic UI components:
 * - Class name management with clsx
 * - Tailwind CSS merge utilities
 * - Performance optimizations
 * - Type safety helpers
 */

import { type ClassValue, clsx } from 'clsx';
import { logger } from '../services/logging/LoggerFactory';

/**
 * Merge Tailwind CSS classes with proper conflict resolution
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number, decimals = 2) {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number,
  immediate?: boolean
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | undefined;

  return function executedFunction(...args: Parameters<T>) {
    const later = function () {
      timeout = undefined;
      if (!immediate) func(...args);
    };

    const callNow = immediate && !timeout;

    clearTimeout(timeout);
    timeout = setTimeout(later, wait);

    if (callNow) func(...args);
  };
}

/**
 * Throttle function for performance optimization
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  
  return function (...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Generate unique ID
 */
export function generateId(prefix = 'id') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Deep merge objects
 */
export function deepMerge<T extends Record<string, unknown>>(
  target: T,
  ...sources: Partial<T>[]
): T {
  if (!sources.length) return target;
  const source = sources.shift();

  if (isObject(target) && isObject(source)) {
    for (const key in source) {
      if (isObject(source[key])) {
        if (!target[key]) Object.assign(target, { [key]: {} });
        deepMerge(target[key], source[key]);
      } else {
        Object.assign(target, { [key]: source[key] });
      }
    }
  }

  return deepMerge(target, ...sources);
}

/**
 * Check if value is an object
 */
export function isObject(item: unknown): item is Record<string, unknown> {
  return item && typeof item === 'object' && !Array.isArray(item);
}

/**
 * Get nested property value safely
 */
export function get<T = unknown>(obj: unknown, path: string, defaultValue?: T): T | undefined {
  const keys = path.split('.');
  let result: unknown = obj as unknown;

  for (const key of keys) {
    if (result == null) return defaultValue;
    result = (result as Record<string, unknown>)[key];
  }
  
  return (result !== undefined ? (result as T) : defaultValue);
}

/**
 * Set nested property value
 */
export function set(obj: unknown, path: string, value: unknown) {
  const keys = path.split('.');
  const lastKey = keys.pop()!;
  let current = obj as Record<string, unknown>;

  for (const key of keys) {
    if ((current as Record<string, unknown>)[key] === undefined || (current as Record<string, unknown>)[key] === null) {
      (current as Record<string, unknown>)[key] = {};
    }
    current = (current as Record<string, unknown>)[key] as Record<string, unknown>;
  }
  
  (current as Record<string, unknown>)[lastKey] = value;
  return obj as unknown;
}

/**
 * Format number with locale
 */
export function formatNumber(num: number, locale = 'en-US') {
  return new Intl.NumberFormat(locale).format(num);
}

/**
 * Format date relative to now
 */
export function formatRelativeTime(date: Date | number | string) {
  const now = new Date();
  const target = new Date(date);
  const diffInSeconds = Math.floor((now.getTime() - target.getTime()) / 1000);

  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  
  return target.toLocaleDateString();
}

/**
 * Escape HTML characters
 */
export function escapeHtml(text: string) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, length: number, suffix = '...') {
  if (text.length <= length) return text;
  return text.substring(0, length - suffix.length) + suffix;
}

/**
 * Convert camelCase to kebab-case
 */
export function camelToKebab(str: string) {
  return str.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
}

/**
 * Convert kebab-case to camelCase
 */
export function kebabToCamel(str: string) {
  return str.replace(/-([a-z])/g, (g) => g[1].toUpperCase());
}

/**
 * Check if element is in viewport
 */
export function isInViewport(element: Element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Smooth scroll to element
 */
export function scrollToElement(element: Element | string, offset = 0) {
  const targetElement = typeof element === 'string' 
    ? document.querySelector(element)
    : element;

  if (!targetElement) return;

  const elementPosition = targetElement.getBoundingClientRect().top + window.pageYOffset;
  const offsetPosition = elementPosition - offset;

  window.scrollTo({
    top: offsetPosition,
    behavior: 'smooth'
  });
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_err) {
    void _err;
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'absolute';
    textArea.style.left = '-999999px';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      document.execCommand('copy');
      return true;
    } catch (_err) {
      void _err;
      return false;
    } finally {
      document.body.removeChild(textArea);
    }
  }
}

/**
 * Detect device type
 */
export function getDeviceType() {
  const userAgent = navigator.userAgent.toLowerCase();
  
  if (/tablet|ipad|playbook|silk/.test(userAgent)) {
    return 'tablet';
  }
  
  if (/mobile|iphone|ipod|android|blackberry|opera|mini|windows\sce|palm|smartphone|iemobile/.test(userAgent)) {
    return 'mobile';
  }
  
  return 'desktop';
}

/**
 * Generate random color
 */
export function generateRandomColor() {
  return `#${Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0')}`;
}

/**
 * Convert hex to RGB
 */
export function hexToRgb(hex: string) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

/**
 * Calculate contrast ratio between two colors
 */
export function getContrastRatio(hex1: string, hex2: string) {
  const rgb1 = hexToRgb(hex1);
  const rgb2 = hexToRgb(hex2);
  
  if (!rgb1 || !rgb2) return 1;

  const getLuminance = (r: number, g: number, b: number) => {
    const [rs, gs, bs] = [r, g, b].map(c => {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  };

  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);

  return (brightest + 0.05) / (darkest + 0.05);
}

/**
 * Performance measurement utility
 */
export class PerformanceMonitor {
  private static marks: Map<string, number> = new Map();

  static start(name: string) {
    this.marks.set(name, performance.now());
  }

  static end(name: string) {
    const start = this.marks.get(name);
    if (start === undefined) {
      logger.warn(`Performance mark "${name}" not found`);
      return 0;
    }

    const end = performance.now();
    const duration = end - start;
    this.marks.delete(name);
    
    if (process.env.NODE_ENV === 'development') {
      logger.info(`⏱️ ${name}: ${duration.toFixed(2)}ms`);
    }
    
    return duration;
  }

  static measure<T>(name: string, fn: () => T): T {
    this.start(name);
    const result = fn();
    this.end(name);
    return result;
  }
}

export default {
  cn,
  formatBytes,
  debounce,
  throttle,
  generateId,
  deepMerge,
  get,
  set,
  formatNumber,
  formatRelativeTime,
  escapeHtml,
  truncate,
  copyToClipboard,
  getDeviceType,
  PerformanceMonitor
};
