/**
 * Plotline API Hooks using TanStack Query
 *
 * Why: Provides type-safe access to Plotline CRUD endpoints with optimistic
 * updates and cache invalidation. Plotlines represent narrative threads that
 * weave through multiple scenes in Director Mode.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import {
  PlotlineResponseSchema,
  PlotlineListResponseSchema,
  PlotlineCreateRequestSchema,
  ScenePlotlinesResponseSchema,
  SetScenePlotlinesRequestSchema,
  type PlotlineResponse,
  type PlotlineListResponse,
  type PlotlineCreateRequest,
  type PlotlineUpdateRequest,
  type ScenePlotlinesResponse,
  type SetScenePlotlinesRequest,
} from '@/types/schemas';

/**
 * Query key factory for plotlines.
 * Why: Centralizes key creation for consistent cache management.
 */
export const plotlineKeys = {
  all: ['plotlines'] as const,
  list: () => [...plotlineKeys.all, 'list'] as const,
  detail: (plotlineId: string) => [...plotlineKeys.all, 'detail', plotlineId] as const,
  scene: (sceneId: string) => [...plotlineKeys.all, 'scene', sceneId] as const,
};

// ============ Raw API Functions ============

/**
 * List all plotlines.
 */
async function listPlotlines(): Promise<PlotlineListResponse> {
  const data = await api.get<unknown>('/structure/plotlines');
  return PlotlineListResponseSchema.parse(data);
}

/**
 * Get a single plotline by ID.
 */
async function getPlotline(plotlineId: string): Promise<PlotlineResponse> {
  const data = await api.get<unknown>(`/structure/plotlines/${plotlineId}`);
  return PlotlineResponseSchema.parse(data);
}

/**
 * Create a new plotline.
 */
async function createPlotline(input: PlotlineCreateRequest): Promise<PlotlineResponse> {
  const payload = PlotlineCreateRequestSchema.parse(input);
  const data = await api.post<unknown>('/structure/plotlines', payload);
  return PlotlineResponseSchema.parse(data);
}

/**
 * Update a plotline.
 */
async function updatePlotline(
  plotlineId: string,
  updates: PlotlineUpdateRequest
): Promise<PlotlineResponse> {
  const data = await api.patch<unknown>(`/structure/plotlines/${plotlineId}`, updates);
  return PlotlineResponseSchema.parse(data);
}

/**
 * Delete a plotline.
 */
async function deletePlotline(plotlineId: string): Promise<void> {
  await api.delete<unknown>(`/structure/plotlines/${plotlineId}`);
}

/**
 * Get all plotlines for a scene.
 */
async function getScenePlotlines(sceneId: string): Promise<ScenePlotlinesResponse> {
  const data = await api.get<unknown>(`/structure/scenes/${sceneId}/plotlines`);
  return ScenePlotlinesResponseSchema.parse(data);
}

/**
 * Link a scene to a plotline.
 */
async function linkSceneToPlotline(
  sceneId: string,
  plotlineId: string
): Promise<ScenePlotlinesResponse> {
  const data = await api.post<unknown>(`/structure/scenes/${sceneId}/plotlines`, {
    plotline_id: plotlineId,
  });
  return ScenePlotlinesResponseSchema.parse(data);
}

/**
 * Unlink a scene from a plotline.
 */
async function unlinkSceneFromPlotline(
  sceneId: string,
  plotlineId: string
): Promise<ScenePlotlinesResponse> {
  const data = await api.delete<unknown>(`/structure/scenes/${sceneId}/plotlines`, {
    body: JSON.stringify({ plotline_id: plotlineId }),
    headers: {
      'Content-Type': 'application/json',
    },
  });
  return ScenePlotlinesResponseSchema.parse(data);
}

/**
 * Set all plotlines for a scene.
 */
async function setScenePlotlines(
  sceneId: string,
  input: SetScenePlotlinesRequest
): Promise<ScenePlotlinesResponse> {
  const payload = SetScenePlotlinesRequestSchema.parse(input);
  const data = await api.put<unknown>(`/structure/scenes/${sceneId}/plotlines`, payload);
  return ScenePlotlinesResponseSchema.parse(data);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch all plotlines.
 */
export function usePlotlines() {
  return useQuery({
    queryKey: plotlineKeys.list(),
    queryFn: listPlotlines,
  });
}

/**
 * Hook to fetch a single plotline.
 */
export function usePlotline(plotlineId: string | undefined) {
  return useQuery({
    queryKey: plotlineKeys.detail(plotlineId ?? ''),
    queryFn: () => getPlotline(plotlineId!),
    enabled: !!plotlineId,
  });
}

/**
 * Hook to fetch plotlines for a scene.
 */
export function useScenePlotlines(sceneId: string | undefined) {
  return useQuery({
    queryKey: plotlineKeys.scene(sceneId ?? ''),
    queryFn: () => getScenePlotlines(sceneId!),
    enabled: !!sceneId,
  });
}

/**
 * Hook to create a new plotline.
 *
 * Why: Provides optimistic updates for immediate UI feedback.
 */
export function useCreatePlotline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: PlotlineCreateRequest) => createPlotline(input),
    onSuccess: () => {
      // Invalidate plotlines list
      queryClient.invalidateQueries({ queryKey: plotlineKeys.list() });
    },
  });
}

/**
 * Hook to update a plotline.
 */
export function useUpdatePlotline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ plotlineId, updates }: { plotlineId: string; updates: PlotlineUpdateRequest }) =>
      updatePlotline(plotlineId, updates),
    onSuccess: (data) => {
      // Update cache with new data
      queryClient.setQueryData(plotlineKeys.detail(data.id), data);
      queryClient.invalidateQueries({ queryKey: plotlineKeys.list() });
    },
  });
}

/**
 * Hook to delete a plotline.
 */
export function useDeletePlotline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (plotlineId: string) => deletePlotline(plotlineId),
    onSuccess: () => {
      // Invalidate all plotlines queries
      queryClient.invalidateQueries({ queryKey: plotlineKeys.all });
    },
  });
}

/**
 * Hook to link a scene to a plotline.
 */
export function useLinkSceneToPlotline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, plotlineId }: { sceneId: string; plotlineId: string }) =>
      linkSceneToPlotline(sceneId, plotlineId),
    onSuccess: (data, variables) => {
      // Update scene plotlines cache
      queryClient.setQueryData(plotlineKeys.scene(variables.sceneId), data);
    },
  });
}

/**
 * Hook to unlink a scene from a plotline.
 */
export function useUnlinkSceneFromPlotline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, plotlineId }: { sceneId: string; plotlineId: string }) =>
      unlinkSceneFromPlotline(sceneId, plotlineId),
    onSuccess: (data, variables) => {
      // Update scene plotlines cache
      queryClient.setQueryData(plotlineKeys.scene(variables.sceneId), data);
    },
  });
}

/**
 * Hook to set all plotlines for a scene.
 */
export function useSetScenePlotlines() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneId, input }: { sceneId: string; input: SetScenePlotlinesRequest }) =>
      setScenePlotlines(sceneId, input),
    onSuccess: (data, variables) => {
      // Update scene plotlines cache
      queryClient.setQueryData(plotlineKeys.scene(variables.sceneId), data);
    },
  });
}

// Export raw functions for non-hook usage
export {
  listPlotlines,
  getPlotline,
  createPlotline,
  updatePlotline,
  deletePlotline,
  getScenePlotlines,
  linkSceneToPlotline,
  unlinkSceneFromPlotline,
  setScenePlotlines,
};
