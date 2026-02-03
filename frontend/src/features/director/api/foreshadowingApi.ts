/**
 * Foreshadowing API hooks for TanStack Query (DIR-052)
 *
 * Provides hooks for managing foreshadowing - Chekhov's Gun tracking
 * for narrative setups and their payoffs.
 */
import { useMutation, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  ForeshadowingResponseSchema,
  ForeshadowingListResponseSchema,
  type ForeshadowingResponse,
  type ForeshadowingListResponse,
  type ForeshadowingCreateRequest,
  type ForeshadowingUpdateRequest,
  type LinkPayoffRequest,
} from '@/types/schemas';

// Query key factory for foreshadowing queries
export const foreshadowingKeys = {
  all: ['foreshadowings'] as const,
  lists: () => [...foreshadowingKeys.all, 'list'] as const,
  list: () => [...foreshadowingKeys.lists()] as const,
  details: () => [...foreshadowingKeys.all, 'detail'] as const,
  detail: (id: string) => [...foreshadowingKeys.details(), id] as const,
};

/**
 * Fetch all foreshadowings
 */
async function fetchForeshadowings(): Promise<ForeshadowingListResponse> {
  const response = await api.get<ForeshadowingListResponse>('/structure/foreshadowings');
  return ForeshadowingListResponseSchema.parse(response);
}

/**
 * Hook to fetch all foreshadowings
 */
export function useForeshadowings(): UseQueryResult<ForeshadowingListResponse, Error> {
  return useQuery({
    queryKey: foreshadowingKeys.list(),
    queryFn: fetchForeshadowings,
  });
}

/**
 * Fetch a single foreshadowing by ID
 */
async function fetchForeshadowing(id: string): Promise<ForeshadowingResponse> {
  const response = await api.get<ForeshadowingResponse>(`/structure/foreshadowings/${id}`);
  return ForeshadowingResponseSchema.parse(response);
}

/**
 * Hook to fetch a single foreshadowing
 */
export function useForeshadowing(
  id: string
): UseQueryResult<ForeshadowingResponse, Error> {
  return useQuery({
    queryKey: foreshadowingKeys.detail(id),
    queryFn: () => fetchForeshadowing(id),
    enabled: !!id,
  });
}

/**
 * Create a new foreshadowing
 */
async function createForeshadowing(
  request: ForeshadowingCreateRequest
): Promise<ForeshadowingResponse> {
  const response = await api.post<ForeshadowingResponse>(
    '/structure/foreshadowings',
    request
  );
  return ForeshadowingResponseSchema.parse(response);
}

/**
 * Hook to create a new foreshadowing
 */
export function useCreateForeshadowing() {
  return useMutation({
    mutationFn: (request: ForeshadowingCreateRequest) => createForeshadowing(request),
  });
}

/**
 * Update a foreshadowing
 */
async function updateForeshadowing(
  id: string,
  request: ForeshadowingUpdateRequest
): Promise<ForeshadowingResponse> {
  const response = await api.put<ForeshadowingResponse>(
    `/structure/foreshadowings/${id}`,
    request
  );
  return ForeshadowingResponseSchema.parse(response);
}

/**
 * Hook to update a foreshadowing
 */
export function useUpdateForeshadowing() {
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: ForeshadowingUpdateRequest }) =>
      updateForeshadowing(id, request),
  });
}

/**
 * Link a payoff scene to a foreshadowing
 */
async function linkPayoff(
  id: string,
  request: LinkPayoffRequest
): Promise<ForeshadowingResponse> {
  const response = await api.post<ForeshadowingResponse>(
    `/structure/foreshadowings/${id}/link-payoff`,
    request
  );
  return ForeshadowingResponseSchema.parse(response);
}

/**
 * Hook to link a payoff scene to a foreshadowing
 */
export function useLinkPayoff() {
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: LinkPayoffRequest }) =>
      linkPayoff(id, request),
  });
}

/**
 * Delete a foreshadowing
 */
async function deleteForeshadowing(id: string): Promise<void> {
  await api.delete(`/structure/foreshadowings/${id}`);
}

/**
 * Hook to delete a foreshadowing
 */
export function useDeleteForeshadowing() {
  return useMutation({
    mutationFn: (id: string) => deleteForeshadowing(id),
  });
}
