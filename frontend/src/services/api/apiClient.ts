import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { store } from '../../store/store';
import { refreshUserToken, logoutUser } from '../../store/slices/authSlice';

// API base configuration
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1';
const API_TIMEOUT = parseInt(process.env.REACT_APP_API_TIMEOUT || '10000');

// Mobile-optimized cache configuration
const MOBILE_CACHE_SIZE = 200; // Reduced from default for mobile memory management
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Simple in-memory cache for mobile optimization
interface CacheEntry {
  data: any;
  timestamp: number;
  expires: number;
}

class MobileAPICache {
  private cache = new Map<string, CacheEntry>();
  private readonly maxSize: number;

  constructor(maxSize: number = MOBILE_CACHE_SIZE) {
    this.maxSize = maxSize;
  }

  set(key: string, data: any, duration: number = CACHE_DURATION): void {
    // Cleanup if cache is full
    if (this.cache.size >= this.maxSize) {
      this.cleanup();
    }

    const now = Date.now();
    this.cache.set(key, {
      data,
      timestamp: now,
      expires: now + duration
    });
  }

  get(key: string): any | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() > entry.expires) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  private cleanup(): void {
    const now = Date.now();
    const entries = Array.from(this.cache.entries());
    
    // Remove expired entries first
    entries.forEach(([key, entry]) => {
      if (now > entry.expires) {
        this.cache.delete(key);
      }
    });

    // If still too full, remove oldest entries
    if (this.cache.size >= this.maxSize) {
      const sortedEntries = entries
        .filter(([key]) => this.cache.has(key))
        .sort(([, a], [, b]) => a.timestamp - b.timestamp);
      
      const toRemove = sortedEntries.slice(0, Math.floor(this.maxSize * 0.3));
      toRemove.forEach(([key]) => this.cache.delete(key));
    }
  }

  clear(): void {
    this.cache.clear();
  }

  getStats(): { size: number; maxSize: number } {
    return { size: this.cache.size, maxSize: this.maxSize };
  }
}

const mobileCache = new MobileAPICache();

// Base API Response structure from OpenAPI spec
export interface BaseAPIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
    recoverable: boolean;
  };
  metadata?: {
    timestamp: string;
    request_id: string;
    version?: string;
    rate_limit?: {
      remaining: number;
      reset_time: string;
    };
  };
}

// Create axios instance
const createAPIClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  });

  // Request interceptor for mobile cache checking
  client.interceptors.request.use(
    (config) => {
      // Check cache for GET requests
      if (config.method === 'get') {
        const cacheKey = `${config.url}_${JSON.stringify(config.params || {})}`;
        const cachedData = mobileCache.get(cacheKey);
        
        if (cachedData) {
          // Return cached response
          return Promise.reject({
            __cached: true,
            data: cachedData,
            status: 200,
            statusText: 'OK',
            headers: {},
            config
          });
        }
      }
      
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Request interceptor to add authentication token
  client.interceptors.request.use(
    (config: AxiosRequestConfig): any => {
      const state = store.getState();
      const token = state.auth.accessToken;
      
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      // Add request ID for tracing
      if (config.headers) {
        config.headers['X-Request-ID'] = generateRequestId();
      }
      
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor for error handling, token refresh, and mobile caching
  client.interceptors.response.use(
    (response: AxiosResponse<BaseAPIResponse>) => {
      // Log rate limit info if available
      if (response.data.metadata?.rate_limit) {
        console.debug('Rate limit:', response.data.metadata.rate_limit);
      }
      
      // Cache GET requests for mobile optimization
      const config = response.config;
      if (config.method === 'get' && response.status === 200) {
        const cacheKey = `${config.url}_${JSON.stringify(config.params || {})}`;
        mobileCache.set(cacheKey, response.data);
      }
      
      return response;
    },
    async (error) => {
      // Handle cached responses
      if (error.__cached) {
        return Promise.resolve(error);
      }

      const originalRequest = error.config;

      // Handle 401 errors (authentication)
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        try {
          // Attempt to refresh token
          await store.dispatch(refreshUserToken());
          
          // Retry original request with new token
          const state = store.getState();
          if (state.auth.accessToken) {
            originalRequest.headers.Authorization = `Bearer ${state.auth.accessToken}`;
            return client(originalRequest);
          }
        } catch (refreshError) {
          // Refresh failed, logout user
          store.dispatch(logoutUser());
          
          // Redirect to login page
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
          
          return Promise.reject(refreshError);
        }
      }

      // Handle 429 (Rate Limit) with automatic retry
      if (error.response?.status === 429) {
        const retryAfter = error.response.headers['retry-after'];
        if (retryAfter && !originalRequest._rateLimitRetry) {
          originalRequest._rateLimitRetry = true;
          
          const delay = parseInt(retryAfter) * 1000; // Convert to milliseconds
          console.warn(`Rate limited. Retrying after ${delay}ms`);
          
          await new Promise(resolve => setTimeout(resolve, delay));
          return client(originalRequest);
        }
      }

      // Transform API error response to standard format
      if (error.response?.data) {
        const apiError = error.response.data as BaseAPIResponse;
        if (apiError.error) {
          error.message = apiError.error.message;
          error.code = apiError.error.code;
          error.recoverable = apiError.error.recoverable;
        }
      }

      return Promise.reject(error);
    }
  );

  return client;
};

// Generate unique request ID for tracing
const generateRequestId = (): string => {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Create and export the API client instance
export const apiClient = createAPIClient();

// Helper function to handle API responses
export const handleAPIResponse = <T>(
  response: AxiosResponse<BaseAPIResponse<T>>
): BaseAPIResponse<T> => {
  return response.data;
};

// Helper function to handle API errors
export const handleAPIError = (error: any): never => {
  console.error('API Error:', error);
  
  // Create standardized error format
  const standardError = {
    message: error.message || 'An unexpected error occurred',
    code: error.code || 'UNKNOWN_ERROR',
    recoverable: error.recoverable !== undefined ? error.recoverable : true,
    originalError: error,
  };
  
  throw standardError;
};

// Health check function
export const healthCheck = async (): Promise<BaseAPIResponse> => {
  try {
    const response = await apiClient.get('/health');
    return handleAPIResponse(response);
  } catch (error) {
    return handleAPIError(error);
  }
};

// Mobile cache management utilities
export const clearAPICache = (): void => {
  mobileCache.clear();
};

export const getAPICacheStats = () => {
  return mobileCache.getStats();
};

// Mobile-optimized request with automatic retry
export const mobileOptimizedRequest = async <T>(
  config: AxiosRequestConfig
): Promise<BaseAPIResponse<T>> => {
  try {
    const response = await apiClient(config);
    return handleAPIResponse<T>(response);
  } catch (error: any) {
    // Handle cached responses
    if (error.__cached) {
      return error.data;
    }
    throw handleAPIError(error);
  }
};

export default apiClient;