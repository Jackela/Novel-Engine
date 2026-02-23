/**
 * Simulation API Hooks using TanStack Query (SIM-031)
 *
 * Provides type-safe access to Simulation endpoints with optimistic
 * updates and cache invalidation for world simulation management.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  SimulateRequestSchema,
  SimulationTickResponseSchema,
  SimulationHistoryResponseSchema,
  CreateSnapshotRequestSchema,
  SnapshotResponseSchema,
  SnapshotListResponseSchema,
  RestoreSnapshotResponseSchema,
} from '@/types/schemas';
import type {
  SimulationTickResponse,
  SimulationHistoryResponse,
  CreateSnapshotRequest,
  SnapshotResponse,
  SnapshotListResponse,
  RestoreSnapshotResponse,
} from '@/types/schemas';

/**
 * Query key factory for simulation.
 * Why: Centralizes key creation for consistent cache management.
 */
const simulationKeys = {
  all: ['simulation'] as const,
  history: (worldId: string) => [...simulationKeys.all, worldId, 'history'] as const,
  tick: (worldId: string, tickId: string) =>
    [...simulationKeys.all, worldId, 'tick', tickId] as const,
};

const snapshotKeys = {
  all: ['snapshots'] as const,
  list: (worldId: string) => [...snapshotKeys.all, worldId, 'list'] as const,
  detail: (worldId: string, snapshotId: string) =>
    [...snapshotKeys.all, worldId, 'detail', snapshotId] as const,
};

// ============ Raw API Functions ============

/**
 * Preview a simulation tick (read-only).
 */
async function previewSimulation(
  worldId: string,
  days: number
): Promise<SimulationTickResponse> {
  const payload = SimulateRequestSchema.parse({ days });
  const data = await api.post<unknown>(
    `/world/${worldId}/simulate/preview`,
    payload
  );
  return SimulationTickResponseSchema.parse(data);
}

/**
 * Commit a simulation tick (persists changes).
 */
async function commitSimulation(
  worldId: string,
  days: number
): Promise<SimulationTickResponse> {
  const payload = SimulateRequestSchema.parse({ days });
  const data = await api.post<unknown>(
    `/world/${worldId}/simulate/commit`,
    payload
  );
  return SimulationTickResponseSchema.parse(data);
}

/**
 * Get simulation history for a world.
 */
async function getSimulationHistory(
  worldId: string,
  limit: number = 20
): Promise<SimulationHistoryResponse> {
  const data = await api.get<unknown>(
    `/world/${worldId}/simulate/history?limit=${limit}`
  );
  return SimulationHistoryResponseSchema.parse(data);
}

/**
 * Get a specific simulation tick.
 */
async function getSimulationTick(
  worldId: string,
  tickId: string
): Promise<SimulationTickResponse> {
  const data = await api.get<unknown>(
    `/world/${worldId}/simulate/${tickId}`
  );
  return SimulationTickResponseSchema.parse(data);
}

/**
 * Create a snapshot.
 */
async function createSnapshot(
  worldId: string,
  request: CreateSnapshotRequest
): Promise<SnapshotResponse> {
  const payload = CreateSnapshotRequestSchema.parse(request);
  const data = await api.post<unknown>(`/world/${worldId}/snapshots`, payload);
  return SnapshotResponseSchema.parse(data);
}

/**
 * List snapshots for a world.
 */
async function listSnapshots(
  worldId: string,
  limit: number = 10
): Promise<SnapshotListResponse> {
  const data = await api.get<unknown>(
    `/world/${worldId}/snapshots?limit=${limit}`
  );
  return SnapshotListResponseSchema.parse(data);
}

/**
 * Restore a snapshot.
 */
async function restoreSnapshot(
  worldId: string,
  snapshotId: string
): Promise<RestoreSnapshotResponse> {
  const data = await api.post<unknown>(
    `/world/${worldId}/snapshots/${snapshotId}/restore`
  );
  return RestoreSnapshotResponseSchema.parse(data);
}

/**
 * Delete a snapshot.
 */
async function deleteSnapshot(
  worldId: string,
  snapshotId: string
): Promise<{ deleted: boolean; snapshot_id: string }> {
  return api.delete<{ deleted: boolean; snapshot_id: string }>(
    `/world/${worldId}/snapshots/${snapshotId}`
  );
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch simulation history for a world.
 *
 * @param worldId - The unique identifier for the world
 * @param limit - Maximum number of ticks to return
 * @returns Query result with simulation history
 */
export function useSimulationHistory(worldId: string | undefined, limit: number = 20) {
  return useQuery({
    queryKey: simulationKeys.history(worldId ?? ''),
    queryFn: () => getSimulationHistory(worldId!, limit),
    enabled: !!worldId,
  });
}

/**
 * Hook to fetch a specific simulation tick.
 *
 * @param worldId - The unique identifier for the world
 * @param tickId - The unique identifier for the tick
 * @returns Query result with tick details
 */
export function useSimulationTick(
  worldId: string | undefined,
  tickId: string | undefined
) {
  return useQuery({
    queryKey: simulationKeys.tick(worldId ?? '', tickId ?? ''),
    queryFn: () => getSimulationTick(worldId!, tickId!),
    enabled: !!worldId && !!tickId,
  });
}

/**
 * Hook to preview a simulation tick (read-only).
 *
 * @returns Mutation hook with mutate function
 */
export function usePreviewSimulation() {
  return useMutation({
    mutationFn: ({ worldId, days }: { worldId: string; days: number }) =>
      previewSimulation(worldId, days),
  });
}

/**
 * Hook to commit a simulation tick (persists changes).
 *
 * Why: Invalidates calendar and simulation history on success.
 *
 * @returns Mutation hook with mutate function
 */
export function useCommitSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ worldId, days }: { worldId: string; days: number }) =>
      commitSimulation(worldId, days),
    onSuccess: (_, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({
        queryKey: simulationKeys.history(variables.worldId),
      });
      queryClient.invalidateQueries({
        queryKey: ['calendar', variables.worldId],
      });
    },
  });
}

/**
 * Hook to fetch snapshots for a world.
 *
 * @param worldId - The unique identifier for the world
 * @param limit - Maximum number of snapshots to return
 * @returns Query result with snapshot list
 */
export function useSnapshots(worldId: string | undefined, limit: number = 10) {
  return useQuery({
    queryKey: snapshotKeys.list(worldId ?? ''),
    queryFn: () => listSnapshots(worldId!, limit),
    enabled: !!worldId,
  });
}

/**
 * Hook to create a snapshot.
 *
 * Why: Invalidates snapshot list on success.
 *
 * @returns Mutation hook with mutate function
 */
export function useCreateSnapshot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      worldId,
      request,
    }: {
      worldId: string;
      request: CreateSnapshotRequest;
    }) => createSnapshot(worldId, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: snapshotKeys.list(variables.worldId),
      });
    },
  });
}

/**
 * Hook to restore a snapshot.
 *
 * Why: Invalidates calendar, simulation history, and snapshots on success.
 *
 * @returns Mutation hook with mutate function
 */
export function useRestoreSnapshot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      worldId,
      snapshotId,
    }: {
      worldId: string;
      snapshotId: string;
    }) => restoreSnapshot(worldId, snapshotId),
    onSuccess: (_, variables) => {
      // Invalidate all relevant queries
      queryClient.invalidateQueries({
        queryKey: simulationKeys.history(variables.worldId),
      });
      queryClient.invalidateQueries({
        queryKey: snapshotKeys.list(variables.worldId),
      });
      queryClient.invalidateQueries({
        queryKey: ['calendar', variables.worldId],
      });
    },
  });
}

/**
 * Hook to delete a snapshot.
 *
 * Why: Invalidates snapshot list on success.
 *
 * @returns Mutation hook with mutate function
 */
export function useDeleteSnapshot() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      worldId,
      snapshotId,
    }: {
      worldId: string;
      snapshotId: string;
    }) => deleteSnapshot(worldId, snapshotId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: snapshotKeys.list(variables.worldId),
      });
    },
  });
}

// Export raw functions for non-hook usage
export {
  previewSimulation,
  commitSimulation,
  getSimulationHistory,
  getSimulationTick,
  createSnapshot,
  listSnapshots,
  restoreSnapshot,
  deleteSnapshot,
};
