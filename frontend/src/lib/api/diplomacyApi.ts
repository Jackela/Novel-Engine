/**
 * Diplomacy API Hooks using TanStack Query (SIM-011)
 *
 * Provides type-safe access to Diplomacy endpoints with
 * cache management and optimistic updates for faction relations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  DiplomacyMatrixResponseSchema,
  FactionDiplomacyResponseSchema,
  SetRelationRequestSchema,
  type DiplomacyMatrixResponse,
  type FactionDiplomacyResponse,
  type DiplomaticStatus,
} from '@/types/schemas';

/**
 * Query key factory for diplomacy.
 * Why: Centralizes key creation for consistent cache management.
 */
const diplomacyKeys = {
  all: ['diplomacy'] as const,
  matrices: () => [...diplomacyKeys.all, 'matrix'] as const,
  matrix: (worldId: string) => [...diplomacyKeys.matrices(), worldId] as const,
  faction: (worldId: string, factionId: string) =>
    [...diplomacyKeys.all, 'faction', worldId, factionId] as const,
};

// ============ Raw API Functions ============

/**
 * Get the full diplomacy matrix for a world.
 */
async function getDiplomacyMatrix(
  worldId: string
): Promise<DiplomacyMatrixResponse> {
  const data = await api.get<unknown>(`/world/${worldId}/diplomacy`);
  return DiplomacyMatrixResponseSchema.parse(data);
}

/**
 * Get diplomatic relations for a single faction.
 */
async function getFactionDiplomacy(
  worldId: string,
  factionId: string
): Promise<FactionDiplomacyResponse> {
  const data = await api.get<unknown>(
    `/world/${worldId}/diplomacy/faction/${factionId}`
  );
  return FactionDiplomacyResponseSchema.parse(data);
}

/**
 * Set the diplomatic relation between two factions.
 */
async function setRelation(
  worldId: string,
  factionA: string,
  factionB: string,
  status: DiplomaticStatus
): Promise<DiplomacyMatrixResponse> {
  const payload = SetRelationRequestSchema.parse({ status });
  const data = await api.put<unknown>(
    `/world/${worldId}/diplomacy/${factionA}/${factionB}`,
    payload
  );
  return DiplomacyMatrixResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch the full diplomacy matrix for a world.
 *
 * @param worldId - The unique identifier for the world
 * @returns Query result with full diplomacy matrix
 */
export function useDiplomacyMatrix(worldId: string | undefined) {
  return useQuery({
    queryKey: diplomacyKeys.matrix(worldId ?? ''),
    queryFn: () => getDiplomacyMatrix(worldId!),
    enabled: !!worldId,
  });
}

/**
 * Hook to fetch a single faction's diplomatic relations.
 *
 * @param worldId - The unique identifier for the world
 * @param factionId - The faction ID to get relations for
 * @returns Query result with faction's allies, enemies, and neutral lists
 */
export function useFactionDiplomacy(
  worldId: string | undefined,
  factionId: string | undefined
) {
  return useQuery({
    queryKey: diplomacyKeys.faction(worldId ?? '', factionId ?? ''),
    queryFn: () => getFactionDiplomacy(worldId!, factionId!),
    enabled: !!worldId && !!factionId,
  });
}

/**
 * Hook to set the diplomatic relation between two factions.
 *
 * Why: Provides optimistic update with rollback on error,
 * and cache invalidation after successful mutation.
 *
 * @returns Mutation hook with mutate function
 */
export function useSetRelation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      worldId,
      factionA,
      factionB,
      status,
    }: {
      worldId: string;
      factionA: string;
      factionB: string;
      status: DiplomaticStatus;
    }) => setRelation(worldId, factionA, factionB, status),
    // Optimistic update: update cache before server responds
    onMutate: async ({ worldId, factionA, factionB, status }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: diplomacyKeys.matrix(worldId),
      });

      // Snapshot the previous value
      const previousMatrix = queryClient.getQueryData<DiplomacyMatrixResponse>(
        diplomacyKeys.matrix(worldId)
      );

      // Optimistically update the matrix
      if (previousMatrix) {
        const updatedMatrix = {
          ...previousMatrix,
          matrix: {
            ...previousMatrix.matrix,
            [factionA]: {
              ...previousMatrix.matrix[factionA],
              [factionB]: status,
            },
            [factionB]: {
              ...previousMatrix.matrix[factionB],
              [factionA]: status,
            },
          },
        };
        queryClient.setQueryData(
          diplomacyKeys.matrix(worldId),
          updatedMatrix
        );
      }

      return { previousMatrix };
    },
    // On error: rollback to snapshot
    onError: (_err, { worldId }, context) => {
      if (context?.previousMatrix) {
        queryClient.setQueryData(
          diplomacyKeys.matrix(worldId),
          context.previousMatrix
        );
      }
    },
    // Always refetch after success or error
    onSettled: (_, __, { worldId }) => {
      queryClient.invalidateQueries({
        queryKey: diplomacyKeys.matrix(worldId),
      });
    },
  });
}

// Export raw functions for non-hook usage
export { getDiplomacyMatrix, getFactionDiplomacy, setRelation };
