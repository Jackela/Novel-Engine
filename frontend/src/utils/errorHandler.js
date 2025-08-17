/**
 * Enhanced Error Handling System for StoryForge AI
 * 
 * Provides user-friendly error messages, automatic retry mechanisms,
 * and recovery suggestions for common issues.
 */

// User-friendly error message mappings
export const ERROR_MESSAGES = {
  // Network and Connection Errors
  'ECONNREFUSED': {
    title: 'Cannot Connect to StoryForge Server',
    message: 'The StoryForge backend server is not running or not accessible.',
    suggestions: [
      'Make sure you have started the backend server',
      'Check if the server is running on http://localhost:8000',
      'Try refreshing the page in a few seconds',
      'Restart the application using ./start.sh'
    ],
    severity: 'error',
    recoverable: true,
    autoRetry: true
  },
  
  'ECONNABORTED': {
    title: 'Request Timed Out',
    message: 'The server is taking too long to respond.',
    suggestions: [
      'The server may be busy generating stories',
      'Try again in a few moments',
      'Check your internet connection',
      'Consider reducing story complexity'
    ],
    severity: 'warning',
    recoverable: true,
    autoRetry: true
  },
  
  'NETWORK_ERROR': {
    title: 'Network Connection Issue',
    message: 'Unable to connect to the internet or StoryForge servers.',
    suggestions: [
      'Check your internet connection',
      'Verify that http://localhost:8000 is accessible',
      'Try refreshing the page',
      'Check if a firewall is blocking the connection'
    ],
    severity: 'error',
    recoverable: true,
    autoRetry: false
  },

  // API and Authentication Errors  
  'API_KEY_INVALID': {
    title: 'Invalid API Key',
    message: 'Your Gemini API key is not valid or has expired.',
    suggestions: [
      'Verify your API key is correct',
      'Check if your API key has expired',
      'Generate a new API key at https://aistudio.google.com/',
      'You can continue without AI features by skipping API setup'
    ],
    severity: 'warning',
    recoverable: true,
    autoRetry: false
  },
  
  'API_QUOTA_EXCEEDED': {
    title: 'API Quota Exceeded',
    message: 'You have exceeded your Gemini API usage limits.',
    suggestions: [
      'Wait for your quota to reset (usually monthly)',
      'Check your usage at https://aistudio.google.com/',
      'Continue with basic features (no AI enhancement)',
      'Consider upgrading your API plan if needed'
    ],
    severity: 'warning',
    recoverable: true,
    autoRetry: false
  },

  'RATE_LIMITED': {
    title: 'Too Many Requests',
    message: 'You are making requests too quickly.',
    suggestions: [
      'Wait a few seconds before trying again',
      'Reduce the frequency of story generation requests',
      'The system will automatically retry in a moment'
    ],
    severity: 'info',
    recoverable: true,
    autoRetry: true
  },

  // Story Generation Errors
  'STORY_GENERATION_FAILED': {
    title: 'Story Generation Failed',
    message: 'Unable to generate the story due to an internal error.',
    suggestions: [
      'Try generating the story again',
      'Check if all characters are properly configured',
      'Verify your internet connection',
      'Try with different story parameters'
    ],
    severity: 'error',
    recoverable: true,
    autoRetry: true
  },
  
  'CHARACTER_LOAD_ERROR': {
    title: 'Character Loading Error',
    message: 'Unable to load one or more characters.',
    suggestions: [
      'Check that character files exist and are properly formatted',
      'Verify character configuration files',
      'Try reloading the page',
      'Create new characters if files are corrupted'
    ],
    severity: 'error',
    recoverable: true,
    autoRetry: false
  },

  // Server and System Errors
  'SERVER_ERROR': {
    title: 'Server Error',
    message: 'The StoryForge server encountered an internal error.',
    suggestions: [
      'Try your request again in a few moments',
      'Check server logs for more details',
      'Restart the server if the issue persists',
      'Report this issue if it continues happening'
    ],
    severity: 'error',
    recoverable: true,
    autoRetry: true
  },

  'CONFIGURATION_ERROR': {
    title: 'Configuration Error',
    message: 'There is an issue with the system configuration.',
    suggestions: [
      'Check your .env file configuration',
      'Verify all required settings are present',
      'Restart the application',
      'Reset to default configuration if needed'
    ],
    severity: 'error',
    recoverable: true,
    autoRetry: false
  },

  // Default fallback
  'UNKNOWN_ERROR': {
    title: 'Unexpected Error',
    message: 'An unexpected error occurred.',
    suggestions: [
      'Try refreshing the page',
      'Check the browser console for more details',
      'Report this issue if it persists',
      'Try restarting the application'
    ],
    severity: 'error',
    recoverable: true,
    autoRetry: false
  }
};

/**
 * Extract error type from various error objects
 */
export function getErrorType(error) {
  // Network errors
  if (error.code === 'ECONNREFUSED') return 'ECONNREFUSED';
  if (error.code === 'ECONNABORTED') return 'ECONNABORTED';
  if (error.message?.includes('Network Error')) return 'NETWORK_ERROR';
  
  // HTTP status errors
  if (error.response?.status === 401) return 'API_KEY_INVALID';
  if (error.response?.status === 429) return 'RATE_LIMITED';
  if (error.response?.status === 403) return 'API_QUOTA_EXCEEDED';
  if (error.response?.status >= 500) return 'SERVER_ERROR';
  
  // Custom error types
  if (error.type) return error.type;
  if (error.message?.includes('Story generation')) return 'STORY_GENERATION_FAILED';
  if (error.message?.includes('Character')) return 'CHARACTER_LOAD_ERROR';
  if (error.message?.includes('Configuration')) return 'CONFIGURATION_ERROR';
  
  return 'UNKNOWN_ERROR';
}

/**
 * Get user-friendly error information
 */
export function getErrorInfo(error) {
  const errorType = getErrorType(error);
  const errorInfo = ERROR_MESSAGES[errorType] || ERROR_MESSAGES.UNKNOWN_ERROR;
  
  return {
    ...errorInfo,
    originalError: error,
    timestamp: new Date().toISOString(),
    errorType
  };
}

/**
 * Enhanced Error Handler Class
 */
export class ErrorHandler {
  constructor() {
    this.retryAttempts = new Map();
    this.maxRetries = 3;
    this.retryDelay = 1000; // Start with 1 second
  }

  /**
   * Handle error with automatic retry logic
   */
  async handleError(error, operation, options = {}) {
    const errorInfo = getErrorInfo(error);
    const operationKey = operation?.name || 'unknown_operation';
    
    // Log error for debugging
    console.error(`Error in ${operationKey}:`, error);
    
    // Check if we should auto-retry
    if (errorInfo.autoRetry && errorInfo.recoverable && options.enableRetry !== false) {
      const attempts = this.retryAttempts.get(operationKey) || 0;
      
      if (attempts < this.maxRetries) {
        this.retryAttempts.set(operationKey, attempts + 1);
        
        // Exponential backoff
        const delay = this.retryDelay * Math.pow(2, attempts);
        
        console.log(`Retrying ${operationKey} in ${delay}ms (attempt ${attempts + 1}/${this.maxRetries})`);
        
        // Show retry notification to user
        if (options.onRetry) {
          options.onRetry({
            attempt: attempts + 1,
            maxAttempts: this.maxRetries,
            delay,
            errorInfo
          });
        }
        
        // Wait and retry
        await new Promise(resolve => setTimeout(resolve, delay));
        
        try {
          const result = await operation();
          // Success - clear retry count
          this.retryAttempts.delete(operationKey);
          return result;
        } catch (retryError) {
          return this.handleError(retryError, operation, options);
        }
      } else {
        // Max retries exceeded
        this.retryAttempts.delete(operationKey);
        errorInfo.retriesExhausted = true;
      }
    }
    
    // Return error info for UI handling
    return { success: false, error: errorInfo };
  }

  /**
   * Clear retry attempts for an operation
   */
  clearRetries(operationKey) {
    this.retryAttempts.delete(operationKey);
  }

  /**
   * Get current retry status
   */
  getRetryStatus(operationKey) {
    return {
      attempts: this.retryAttempts.get(operationKey) || 0,
      maxRetries: this.maxRetries
    };
  }
}

/**
 * Global error handler instance
 */
export const globalErrorHandler = new ErrorHandler();

/**
 * Create a wrapped version of an async function with error handling
 */
export function withErrorHandling(asyncFunction, options = {}) {
  return async (...args) => {
    try {
      const result = await asyncFunction(...args);
      return { success: true, data: result };
    } catch (error) {
      return globalErrorHandler.handleError(error, asyncFunction, options);
    }
  };
}

import React from 'react';

/**
 * React hook for error handling
 */
export function useErrorHandler() {
  const [error, setError] = React.useState(null);
  const [isRetrying, setIsRetrying] = React.useState(false);
  const [retryStatus, setRetryStatus] = React.useState(null);

  const handleError = React.useCallback(async (error, operation, options = {}) => {
    setError(null);
    setIsRetrying(false);
    setRetryStatus(null);

    const result = await globalErrorHandler.handleError(error, operation, {
      ...options,
      onRetry: (status) => {
        setIsRetrying(true);
        setRetryStatus(status);
        if (options.onRetry) options.onRetry(status);
      }
    });

    if (!result.success) {
      setError(result.error);
      setIsRetrying(false);
      setRetryStatus(null);
    }

    return result;
  }, []);

  const clearError = React.useCallback(() => {
    setError(null);
    setIsRetrying(false);
    setRetryStatus(null);
  }, []);

  return {
    error,
    isRetrying,
    retryStatus,
    handleError,
    clearError
  };
}

// Note: React import is commented out since this is a utility file
// Users of useErrorHandler should import React in their components