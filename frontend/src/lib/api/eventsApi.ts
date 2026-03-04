/**
 * Events API Hooks using TanStack Query (SIM-007)
 *
 * Provides type-safe access to Historical Events endpoints with
 * cache management and optimistic updates for world timeline.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  EventListResponseSchema,
  HistoryEventResponseSchema,
  CreateEventRequestSchema,
  type EventListResponse,
  type HistoryEventResponse,
  type EventFilterParams,
  type CreateEventRequest,
} from '@/types/schemas';

/**
 * Query key factory for events.
 * Why: Centralizes key creation for consistent cache management.
 */
const eventsKeys = {
  all: ['events'] as const,
  lists: () => [...eventsKeys.all, 'list'] as const,
  list: (worldId: string, filters?: EventFilterParams) =>
    [...eventsKeys.lists(), worldId, filters] as const,
  details: () => [...eventsKeys.all, 'detail'] as const,
  detail: (worldId: string, eventId: string) =>
    [...eventsKeys.details(), worldId, eventId] as const,
};

// ============ Raw API Functions ============

/**
 * Get paginated list of historical events for a world.
 */
async function getWorldEvents(
  worldId: string,
  filters?: EventFilterParams
): Promise<EventListResponse> {
  const params = new URLSearchParams();

  if (filters) {
    if (filters.event_type) params.append('event_type', filters.event_type);
    if (filters.impact_scope) params.append('impact_scope', filters.impact_scope);
    if (filters.from_date) params.append('from_date', filters.from_date);
    if (filters.to_date) params.append('to_date', filters.to_date);
    if (filters.faction_id) params.append('faction_id', filters.faction_id);
    if (filters.location_id) params.append('location_id', filters.location_id);
    if (filters.is_secret !== undefined)
      params.append('is_secret', String(filters.is_secret));
    params.append('page', String(filters.page ?? 1));
    params.append('page_size', String(filters.page_size ?? 20));
  }

  const queryString = params.toString();
  const url = `/world/${worldId}/events${queryString ? `?${queryString}` : ''}`;

  const data = await api.get<unknown>(url);
  return EventListResponseSchema.parse(data);
}

/**
 * Get a single historical event by ID.
 */
async function getWorldEvent(
  worldId: string,
  eventId: string
): Promise<HistoryEventResponse> {
  const data = await api.get<unknown>(`/world/${worldId}/events/${eventId}`);
  return HistoryEventResponseSchema.parse(data);
}

/**
 * Create a new historical event.
 */
async function createWorldEvent(
  worldId: string,
  request: CreateEventRequest
): Promise<HistoryEventResponse> {
  const payload = CreateEventRequestSchema.parse(request);
  const data = await api.post<unknown>(`/world/${worldId}/events`, payload);
  return HistoryEventResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch paginated historical events for a world.
 *
 * @param worldId - The unique identifier for the world
 * @param filters - Optional filter parameters (event_type, impact_scope, etc.)
 * @returns Query result with paginated events list
 */
export function useWorldEvents(
  worldId: string | undefined,
  filters?: EventFilterParams
) {
  return useQuery({
    queryKey: eventsKeys.list(worldId ?? '', filters),
    queryFn: () => getWorldEvents(worldId!, filters),
    enabled: !!worldId,
  });
}

/**
 * Hook to fetch a single historical event by ID.
 *
 * @param worldId - The unique identifier for the world
 * @param eventId - The unique identifier for the event
 * @returns Query result with event details
 */
export function useWorldEvent(
  worldId: string | undefined,
  eventId: string | undefined
) {
  return useQuery({
    queryKey: eventsKeys.detail(worldId ?? '', eventId ?? ''),
    queryFn: () => getWorldEvent(worldId!, eventId!),
    enabled: !!worldId && !!eventId,
  });
}

/**
 * Alias for useWorldEvent for simpler naming.
 * Hook to fetch a single historical event by ID.
 *
 * @param worldId - The unique identifier for the world
 * @param eventId - The unique identifier for the event
 * @returns Query result with event details
 */
export function useEvent(
  worldId: string | undefined,
  eventId: string | undefined
) {
  return useWorldEvent(worldId, eventId);
}

/**
 * Hook to create a new historical event.
 *
 * Why: Provides cache invalidation after creation to refresh timeline.
 *
 * @returns Mutation hook with mutate function
 */
export function useCreateEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      worldId,
      request,
    }: {
      worldId: string;
      request: CreateEventRequest;
    }) => createWorldEvent(worldId, request),
    // Invalidate events list after creation
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: eventsKeys.lists(),
      });
    },
  });
}

// Export raw functions for non-hook usage
export { getWorldEvents, getWorldEvent, createWorldEvent };
