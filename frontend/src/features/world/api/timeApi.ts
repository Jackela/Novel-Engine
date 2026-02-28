/**
 * World Time API Client
 *
 * This module provides TanStack Query hooks for interacting with the world time API.
 * It handles fetching the current world time and advancing time.
 *
 * ## Error Handling Approach
 *
 * Errors are NOT handled in onError callbacks. Instead, they propagate through
 * TanStack Query's built-in error state (`mutation.error`, `query.error`).
 * Consumers should check these error states to display appropriate UI feedback.
 *
 * @module features/world/api/timeApi
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';

import { AdvanceTimeRequestSchema, WorldTimeResponseSchema } from '@/types/schemas';

import type { WorldTimeResponse, AdvanceTimeRequest } from '@/types/schemas';

// API base URL - use relative path for proxy support
const API_BASE = '/api';

/**
 * Query keys for world time related queries.
 */
export const worldTimeKeys = {
  all: ['world', 'time'] as const,
  time: () => [...worldTimeKeys.all, 'current'] as const,
};

/**
 * Parse an error response from the API.
 *
 * Attempts to extract error details from the response body. Handles both
 * JSON error responses and plain text responses gracefully.
 *
 * @param response - The failed fetch Response object
 * @param context - Context string describing the operation (e.g., "fetch world time")
 * @returns Promise resolving to an Error with detailed message
 */
async function parseErrorResponse(response: Response, context: string): Promise<Error> {
  const statusInfo = `Status: ${response.status} ${response.statusText}`;

  // Try to parse as JSON first
  try {
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      const errorData = await response.json();
      // Handle FastAPI-style error responses
      const detail = errorData.detail;
      if (typeof detail === 'string') {
        return new Error(`${context} failed: ${detail} (${statusInfo})`);
      }
      if (detail?.message) {
        return new Error(`${context} failed: ${detail.message} (${statusInfo})`);
      }
      if (errorData.message) {
        return new Error(`${context} failed: ${errorData.message} (${statusInfo})`);
      }
    }
  } catch {
    // JSON parsing failed, fall through to text parsing
  }

  // Try to get plain text response
  try {
    const text = await response.text();
    if (text) {
      return new Error(`${context} failed: ${text} (${statusInfo})`);
    }
  } catch {
    // Text parsing failed, use generic message
  }

  // Fallback to status-based error
  return new Error(`${context} failed (${statusInfo})`);
}

/**
 * Fetch the current world time from the API.
 *
 * @returns Promise resolving to the current world time
 * @throws Error if the request fails, with detailed context including status code
 */
async function fetchWorldTime(): Promise<WorldTimeResponse> {
  const response = await fetch(`${API_BASE}/world/time`);

  if (!response.ok) {
    throw await parseErrorResponse(response, 'Fetch world time');
  }

  const data = await response.json();
  return WorldTimeResponseSchema.parse(data);
}

/**
 * Advance the world time by a specified number of days.
 *
 * @param days - Number of days to advance (must be >= 1)
 * @returns Promise resolving to the updated world time
 * @throws Error if the request fails or validation fails, with detailed context including status code
 */
async function advanceWorldTime(days: number): Promise<WorldTimeResponse> {
  // Validate request
  const request: AdvanceTimeRequest = AdvanceTimeRequestSchema.parse({ days });

  const response = await fetch(`${API_BASE}/world/time/advance`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response, 'Advance time');
  }

  const data = await response.json();
  return WorldTimeResponseSchema.parse(data);
}

/**
 * Hook to fetch the current world time.
 *
 * This hook uses TanStack Query to manage fetching and caching the world time.
 * The time is automatically refreshed based on the staleTime configuration.
 *
 * @returns UseQueryResult containing the world time data
 *
 * @example
 * ```tsx
 * function WorldTimeDisplay() {
 *   const { data, isLoading, error } = useWorldTime();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return <div>{data?.display_string}</div>;
 * }
 * ```
 */
export function useWorldTime(): UseQueryResult<WorldTimeResponse, Error> {
  return useQuery({
    queryKey: worldTimeKeys.time(),
    queryFn: fetchWorldTime,
    staleTime: 1000 * 60 * 5, // 5 minutes - time doesn't change often
    gcTime: 1000 * 60 * 30, // 30 minutes garbage collection
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to advance the world time.
 *
 * This hook provides a mutation function to advance the world time by a
 * specified number of days. On success, it automatically invalidates
 * the world time query to trigger a refetch.
 *
 * ## Error Handling
 *
 * Errors are NOT caught internally. Instead, they are available via `mutation.error`.
 * Consumers should check this property to display error feedback to users.
 *
 * @returns UseMutationResult for advancing time
 *
 * @example
 * ```tsx
 * function AdvanceTimeButton() {
 *   const advanceTime = useAdvanceTime();
 *
 *   const handleAdvance = (days: number) => {
 *     advanceTime.mutate(days);
 *   };
 *
 *   return (
 *     <div>
 *       {advanceTime.error && (
 *         <div className="error">Failed: {advanceTime.error.message}</div>
 *       )}
 *       <button
 *         onClick={() => handleAdvance(7)}
 *         disabled={advanceTime.isPending}
 *       >
 *         Advance 7 Days
 *       </button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useAdvanceTime(): UseMutationResult<
  WorldTimeResponse,
  Error,
  number,
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: advanceWorldTime,
    onSuccess: (data) => {
      // Update the cached time data immediately
      queryClient.setQueryData(worldTimeKeys.time(), data);
    },
    // NOTE: No onError callback here. Errors are propagated to mutation.error
    // so consumers can handle them in the UI (e.g., toast notifications, error messages).
    // This follows TanStack Query best practices for error handling.
  });
}

/**
 * Convenience hook that combines useWorldTime and useAdvanceTime.
 *
 * Provides easy access to the current time and a function to advance it.
 *
 * @returns Object with time data, advance function, and status flags
 *
 * @example
 * ```tsx
 * function TimeControls() {
 *   const { time, advanceTime, isLoading, isAdvancing } = useWorldTimeControls();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *
 *   return (
 *     <div>
 *       <p>Current: {time?.display_string}</p>
 *       <button
 *         onClick={() => advanceTime(1)}
 *         disabled={isAdvancing}
 *       >
 *         Advance 1 Day
 *       </button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useWorldTimeControls() {
  const timeQuery = useWorldTime();
  const advanceMutation = useAdvanceTime();

  return {
    time: timeQuery.data,
    isLoading: timeQuery.isLoading,
    isAdvancing: advanceMutation.isPending,
    error: timeQuery.error || advanceMutation.error,
    advanceTime: advanceMutation.mutate,
    advanceTimeAsync: advanceMutation.mutateAsync,
    refetch: timeQuery.refetch,
  };
}
