/**
 * Rumors API Hooks using TanStack Query (SIM-026)
 *
 * Provides type-safe access to Rumors endpoints with
 * cache management for world rumors.
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  RumorListResponseSchema,
  RumorResponseSchema,
  type RumorListResponse,
  type RumorResponse,
  type RumorSortBy,
} from '@/types/schemas';

/**
 * Query key factory for rumors.
 * Why: Centralizes key creation for consistent cache management.
 */
const rumorsKeys = {
  all: ['rumors'] as const,
  lists: () => [...rumorsKeys.all, 'list'] as const,
  list: (worldId: string, locationId?: string, sortBy?: RumorSortBy) =>
    [...rumorsKeys.lists(), worldId, locationId, sortBy] as const,
  details: () => [...rumorsKeys.all, 'detail'] as const,
  detail: (worldId: string, rumorId: string) =>
    [...rumorsKeys.details(), worldId, rumorId] as const,
};

// ============ Raw API Functions ============

/**
 * Get list of rumors for a world with optional filters.
 */
async function getRumors(
  worldId: string,
  locationId?: string,
  sortBy: RumorSortBy = 'recent',
  limit: number = 20
): Promise<RumorListResponse> {
  const params = new URLSearchParams();

  if (locationId) {
    params.append('location_id', locationId);
  }
  params.append('sort_by', sortBy);
  params.append('limit', String(limit));

  const queryString = params.toString();
  const url = `/world/${worldId}/rumors${queryString ? `?${queryString}` : ''}`;

  const data = await api.get<unknown>(url);
  return RumorListResponseSchema.parse(data);
}

/**
 * Get a single rumor by ID.
 */
async function getRumor(worldId: string, rumorId: string): Promise<RumorResponse> {
  const data = await api.get<unknown>(`/world/${worldId}/rumors/${rumorId}`);
  return RumorResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch rumors for a world with optional filtering and sorting.
 *
 * @param worldId - The unique identifier for the world
 * @param locationId - Optional filter for rumors at a specific location
 * @param sortBy - Sort order (recent, reliable, spread)
 * @param limit - Maximum number of results (default 20)
 * @returns Query result with rumors list
 */
export function useRumors(
  worldId: string | undefined,
  locationId?: string,
  sortBy: RumorSortBy = 'recent',
  limit: number = 20
) {
  return useQuery({
    queryKey: rumorsKeys.list(worldId ?? '', locationId, sortBy),
    queryFn: () => getRumors(worldId!, locationId, sortBy, limit),
    enabled: !!worldId,
  });
}

/**
 * Hook to fetch a single rumor by ID.
 *
 * @param worldId - The unique identifier for the world
 * @param rumorId - The unique identifier for the rumor
 * @returns Query result with rumor details
 */
export function useRumor(worldId: string | undefined, rumorId: string | undefined) {
  return useQuery({
    queryKey: rumorsKeys.detail(worldId ?? '', rumorId ?? ''),
    queryFn: () => getRumor(worldId!, rumorId!),
    enabled: !!worldId && !!rumorId,
  });
}

/**
 * Hook to fetch rumors for a specific location.
 * Alias for useRumors with locationId required.
 *
 * @param worldId - The unique identifier for the world
 * @param locationId - The specific location to filter rumors by
 * @param sortBy - Sort order (recent, reliable, spread)
 * @param limit - Maximum number of results (default 20)
 * @returns Query result with rumors list for the location
 */
export function useLocationRumors(
  worldId: string | undefined,
  locationId: string | undefined,
  sortBy: RumorSortBy = 'recent',
  limit: number = 20
) {
  return useRumors(worldId, locationId, sortBy, limit);
}

// Export raw functions for non-hook usage
export { getRumors, getRumor };
