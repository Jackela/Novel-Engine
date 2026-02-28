/**
 * Faction Intel API Client
 *
 * This module provides TanStack Query hooks for interacting with the faction AI
 * intent generation system. It handles generating, fetching, and selecting
 * faction intents for world simulation.
 *
 * ## Error Handling Approach
 *
 * Errors are NOT handled in onError callbacks. Instead, they propagate through
 * TanStack Query's built-in error state (`mutation.error`, `query.error`).
 * Consumers should check these error states to display appropriate UI feedback.
 *
 * @module features/world/api/factionIntelApi
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseMutationResult, UseQueryResult } from '@tanstack/react-query';

import {
  FactionIntentListResponseSchema,
  GenerateIntentsResponseSchema,
  SelectIntentResponseSchema,
} from '@/types/schemas';

import type {
  FactionIntentListResponse,
  GenerateIntentsRequest,
  GenerateIntentsResponse,
  IntentStatus,
  SelectIntentResponse,
} from '@/types/schemas';

// API base URL - use relative path for proxy support
const API_BASE = '/api/world/factions';

/**
 * Query keys for faction intel related queries.
 * Uses a hierarchical structure for efficient cache invalidation.
 */
export const factionIntelKeys = {
  all: ['faction-intel'] as const,
  faction: (factionId: string) => [...factionIntelKeys.all, factionId] as const,
  intents: (factionId: string) => [...factionIntelKeys.faction(factionId), 'intents'] as const,
  intentsWithStatus: (factionId: string, status?: IntentStatus) =>
    [...factionIntelKeys.intents(factionId), status] as const,
};

/**
 * Parse an error response from the API.
 *
 * Attempts to extract error details from the response body. Handles both
 * JSON error responses and plain text responses gracefully.
 *
 * @param response - The failed fetch Response object
 * @param context - Context string describing the operation (e.g., "generate intents")
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
 * Fetch intents for a faction, optionally filtered by status.
 *
 * @param factionId - The faction ID to fetch intents for
 * @param status - Optional status filter (PROPOSED, SELECTED, EXECUTED, REJECTED)
 * @returns Promise resolving to the intent list response
 * @throws Error if the request fails, with detailed context including status code
 */
async function fetchFactionIntents(
  factionId: string,
  status?: IntentStatus
): Promise<FactionIntentListResponse> {
  const url = new URL(`${API_BASE}/${factionId}/intents`, window.location.origin);
  if (status) {
    url.searchParams.set('status', status);
  }

  const response = await fetch(url.pathname + url.search);

  if (!response.ok) {
    throw await parseErrorResponse(response, 'Fetch faction intents');
  }

  const data = await response.json();
  return FactionIntentListResponseSchema.parse(data);
}

/**
 * Generate new AI intents for a faction.
 *
 * @param request - The generation request with faction_id and options
 * @returns Promise resolving to the generated intents
 * @throws Error if the request fails, with detailed context including status code
 */
async function generateIntents(request: GenerateIntentsRequest): Promise<GenerateIntentsResponse> {
  const { faction_id, ...body } = request;

  const response = await fetch(`${API_BASE}/${faction_id}/decide`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response, 'Generate intents');
  }

  const data = await response.json();
  return GenerateIntentsResponseSchema.parse(data);
}

/**
 * Select an intent for execution.
 *
 * @param factionId - The faction ID
 * @param intentId - The intent ID to select
 * @returns Promise resolving to the selection response
 * @throws Error if the request fails, with detailed context including status code
 */
async function selectIntent(factionId: string, intentId: string): Promise<SelectIntentResponse> {
  const response = await fetch(`${API_BASE}/${factionId}/intents/${intentId}/select`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw await parseErrorResponse(response, 'Select intent');
  }

  const data = await response.json();
  return SelectIntentResponseSchema.parse(data);
}

/**
 * Hook to fetch faction intents with optional status filter.
 *
 * This hook uses TanStack Query to manage fetching and caching faction intents.
 * The intents are automatically refreshed when the component mounts or when
 * the cache is invalidated.
 *
 * @param factionId - The faction ID to fetch intents for
 * @param status - Optional status filter
 * @returns UseQueryResult containing the faction intents data
 *
 * @example
 * ```tsx
 * function IntentList({ factionId }: { factionId: string }) {
 *   const { data, isLoading, error } = useFactionIntents(factionId, 'PROPOSED');
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <ul>
 *       {data?.intents.map(intent => (
 *         <li key={intent.intent_id}>{intent.rationale}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 * ```
 */
export function useFactionIntents(
  factionId: string,
  status?: IntentStatus
): UseQueryResult<FactionIntentListResponse, Error> {
  return useQuery({
    queryKey: factionIntelKeys.intentsWithStatus(factionId, status),
    queryFn: () => fetchFactionIntents(factionId, status),
    enabled: !!factionId,
    staleTime: 1000 * 30, // 30 seconds - intents can change
    gcTime: 1000 * 60 * 5, // 5 minutes garbage collection
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook to generate new AI intents for a faction.
 *
 * This hook provides a mutation function to trigger AI intent generation.
 * On success, it automatically invalidates the faction intents query to
 * trigger a refetch of the updated intent list.
 *
 * ## Error Handling
 *
 * Errors are NOT caught internally. Instead, they are available via `mutation.error`.
 * Consumers should check this property to display error feedback to users.
 *
 * @returns UseMutationResult for generating intents
 *
 * @example
 * ```tsx
 * function GenerateButton({ factionId }: { factionId: string }) {
 *   const generate = useGenerateIntents();
 *
 *   const handleGenerate = () => {
 *     generate.mutate({ faction_id: factionId, max_intents: 3 });
 *   };
 *
 *   return (
 *     <div>
 *       {generate.error && (
 *         <div className="error">Failed: {generate.error.message}</div>
 *       )}
 *       <button
 *         onClick={handleGenerate}
 *         disabled={generate.isPending}
 *       >
 *         {generate.isPending ? 'Generating...' : 'Generate Intents'}
 *       </button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useGenerateIntents(): UseMutationResult<
  GenerateIntentsResponse,
  Error,
  GenerateIntentsRequest,
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: generateIntents,
    onSuccess: (data) => {
      // Invalidate all intent queries for this faction to trigger refetch
      queryClient.invalidateQueries({
        queryKey: factionIntelKeys.intents(data.faction_id),
      });
    },
    // NOTE: No onError callback here. Errors are propagated to mutation.error
    // so consumers can handle them in the UI (e.g., toast notifications, error messages).
    // This follows TanStack Query best practices for error handling.
  });
}

/**
 * Hook to select an intent for execution.
 *
 * This hook provides a mutation function to select a proposed intent.
 * On success, it automatically invalidates the faction intents query to
 * reflect the status change.
 *
 * ## Error Handling
 *
 * Errors are NOT caught internally. Instead, they are available via `mutation.error`.
 * Consumers should check this property to display error feedback to users.
 *
 * @returns UseMutationResult for selecting an intent
 *
 * @example
 * ```tsx
 * function IntentCard({ intent }: { intent: FactionIntentResponse }) {
 *   const selectIntent = useSelectIntent();
 *
 *   const handleSelect = () => {
 *     selectIntent.mutate({
 *       factionId: intent.faction_id,
 *       intentId: intent.intent_id,
 *     });
 *   };
 *
 *   return (
 *     <button
 *       onClick={handleSelect}
 *       disabled={intent.status !== 'PROPOSED' || selectIntent.isPending}
 *     >
 *       {selectIntent.isPending ? 'Selecting...' : 'Select'}
 *     </button>
 *   );
 * }
 * ```
 */
export function useSelectIntent(): UseMutationResult<
  SelectIntentResponse,
  Error,
  { factionId: string; intentId: string },
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ factionId, intentId }) => selectIntent(factionId, intentId),
    onSuccess: (data) => {
      // Invalidate all intent queries for this faction to trigger refetch
      queryClient.invalidateQueries({
        queryKey: factionIntelKeys.intents(data.faction_id),
      });
    },
    // NOTE: No onError callback here. Errors are propagated to mutation.error
    // so consumers can handle them in the UI.
  });
}

/**
 * Convenience hook that combines all faction intel operations.
 *
 * Provides easy access to intents, generation, and selection functions.
 *
 * @param factionId - The faction ID to operate on
 * @param status - Optional status filter for intents query
 * @returns Object with intents data, mutation functions, and status flags
 *
 * @example
 * ```tsx
 * function FactionIntelPanel({ factionId }: { factionId: string }) {
 *   const {
 *     intents,
 *     isLoading,
 *     generateIntents,
 *     selectIntent,
 *     isGenerating,
 *     error,
 *   } = useFactionIntel(factionId, 'PROPOSED');
 *
 *   if (isLoading) return <div>Loading...</div>;
 *
 *   return (
 *     <div>
 *       {error && <div className="error">{error.message}</div>}
 *       <button
 *         onClick={() => generateIntents({ faction_id: factionId })}
 *         disabled={isGenerating}
 *       >
 *         Generate Intents
 *       </button>
 *       <ul>
 *         {intents?.intents.map(intent => (
 *           <li key={intent.intent_id}>
 *             {intent.rationale}
 *             <button onClick={() => selectIntent({ factionId, intentId: intent.intent_id })}>
 *               Select
 *             </button>
 *           </li>
 *         ))}
 *       </ul>
 *     </div>
 *   );
 * }
 * ```
 */
export function useFactionIntel(factionId: string, status?: IntentStatus) {
  const intentsQuery = useFactionIntents(factionId, status);
  const generateMutation = useGenerateIntents();
  const selectMutation = useSelectIntent();

  return {
    // Query data
    intents: intentsQuery.data,
    totalIntents: intentsQuery.data?.total ?? 0,

    // Loading states
    isLoading: intentsQuery.isLoading,
    isGenerating: generateMutation.isPending,
    isSelecting: selectMutation.isPending,

    // Error states
    error: intentsQuery.error || generateMutation.error || selectMutation.error,
    queryError: intentsQuery.error,
    generateError: generateMutation.error,
    selectError: selectMutation.error,

    // Actions
    generateIntents: generateMutation.mutate,
    generateIntentsAsync: generateMutation.mutateAsync,
    selectIntent: selectMutation.mutate,
    selectIntentAsync: selectMutation.mutateAsync,

    // Utilities
    refetch: intentsQuery.refetch,
    isFetching: intentsQuery.isFetching,
  };
}
