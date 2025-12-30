/**
 * API Client Compatibility Layer
 * 
 * Centralizes the implementation in src/lib/api/apiClient.ts and re-exports
 * everything to maintain backward compatibility.
 */

import apiClient, { 
  createAuthenticatedAPIClient, 
  handleAPIError, 
  handleAPIResponse,
} from '../../lib/api/apiClient';
import type { BaseAPIResponse } from '../../lib/api/apiClient';

// Re-export the singleton instance as the default
export default apiClient;

// Re-export named members
export { 
  apiClient, 
  createAuthenticatedAPIClient, 
  handleAPIError,
  handleAPIResponse,
  type BaseAPIResponse 
};

/**
 * Mobile cache management utilities (Stubs)
 */
export const clearAPICache = (): void => {};
export const getAPICacheStats = () => ({ size: 0, maxSize: 0 });

export const mobileOptimizedRequest = async <T>(config: any): Promise<BaseAPIResponse<T>> => {
  try {
    const response = await apiClient(config);
    return response.data;
  } catch (error) {
    throw handleAPIError(error);
  }
};