/**
 * Environment Configuration Module
 * 
 * Centralizes access to environment variables to ensure type safety and validation.
 * Replaces direct usage of `import.meta.env` or `process.env` throughout the app.
 */

export interface EnvConfig {
  /**
   * Enable Guest/Demo mode without requiring backend authentication.
   * Default: true
   */
  enableGuestMode: boolean;

  /**
   * Base URL for the API.
   * Default: empty string (relative path)
   */
  apiBaseUrl: string;

  /**
   * API Timeout in milliseconds.
   * Default: 10000
   */
  apiTimeout: number;
}

const getEnvVar = (key: string, fallback: string): string => {
  // Check import.meta.env (Vite)
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env[key]) {
    return String(import.meta.env[key]);
  }
  // Check process.env (Node/Jest/Legacy)
  if (typeof process !== 'undefined' && process.env && process.env[key]) {
    return String(process.env[key]);
  }
  return fallback;
};

const getBoolEnvVar = (key: string, fallback: boolean): boolean => {
  const val = getEnvVar(key, String(fallback)).toLowerCase().trim();
  return val === 'true' || val === '1';
};

const getNumberEnvVar = (key: string, fallback: number): number => {
  const val = getEnvVar(key, String(fallback));
  const parsed = parseInt(val, 10);
  return isNaN(parsed) ? fallback : parsed;
};

export const config: EnvConfig = {
  enableGuestMode: getBoolEnvVar('VITE_ENABLE_GUEST_MODE', true), // Default to true as per existing logic
  apiBaseUrl: getEnvVar('VITE_API_BASE_URL', ''),
  apiTimeout: getNumberEnvVar('VITE_API_TIMEOUT', 10000),
};

export default config;
