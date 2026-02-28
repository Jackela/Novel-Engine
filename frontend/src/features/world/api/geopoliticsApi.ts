/**
 * Geopolitics API hooks
 *
 * Unified API hooks for geopolitics operations including diplomacy,
 * territory control, and resources.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  DiplomacyMatrixDetailResponseSchema,
  TerritoriesResponseSchema,
  WorldResourcesResponseSchema,
  WarResponseSchema,
  AllianceResponseSchema,
  TerritoryTransferResponseSchema,
} from '@/types/schemas';
import type {
  DeclareWarRequest,
  FormAllianceRequest,
  TransferTerritoryRequest,
} from '@/types/schemas';

const API_BASE = '/api/geopolitics';

// Query keys
export const geopoliticsKeys = {
  all: ['geopolitics'] as const,
  world: (worldId: string) => [...geopoliticsKeys.all, worldId] as const,
  diplomacy: (worldId: string) => [...geopoliticsKeys.world(worldId), 'diplomacy'] as const,
  territories: (worldId: string) => [...geopoliticsKeys.world(worldId), 'territories'] as const,
  resources: (worldId: string) => [...geopoliticsKeys.world(worldId), 'resources'] as const,
};

// Error parsing helper
async function parseErrorResponse(response: Response, operation: string): Promise<Error> {
  try {
    const data = await response.json();
    const message = data?.detail || data?.message || `Failed to ${operation}`;
    return new Error(message);
  } catch {
    return new Error(`Failed to ${operation}: HTTP ${response.status}`);
  }
}

// === Query Hooks ===

export function useDiplomacy(worldId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: geopoliticsKeys.diplomacy(worldId),
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/world/${worldId}/diplomacy`);
      if (!response.ok) throw await parseErrorResponse(response, 'fetch diplomacy');
      const data = await response.json();
      return DiplomacyMatrixDetailResponseSchema.parse(data);
    },
    enabled: options?.enabled ?? true,
  });
}

export function useTerritories(worldId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: geopoliticsKeys.territories(worldId),
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/world/${worldId}/territories`);
      if (!response.ok) {
        if (response.status === 404) return null;
        throw await parseErrorResponse(response, 'fetch territories');
      }
      const data = await response.json();
      return TerritoriesResponseSchema.parse(data);
    },
    enabled: options?.enabled ?? true,
  });
}

export function useResources(worldId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: geopoliticsKeys.resources(worldId),
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/world/${worldId}/resources`);
      if (!response.ok) {
        if (response.status === 404) return null;
        throw await parseErrorResponse(response, 'fetch resources');
      }
      const data = await response.json();
      return WorldResourcesResponseSchema.parse(data);
    },
    enabled: options?.enabled ?? true,
  });
}

// === Mutation Hooks ===

export function useDeclareWar(worldId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: DeclareWarRequest) => {
      const response = await fetch(`${API_BASE}/world/${worldId}/war`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!response.ok) throw await parseErrorResponse(response, 'declare war');
      const data = await response.json();
      return WarResponseSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.diplomacy(worldId) });
    },
  });
}

export function useFormAlliance(worldId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: FormAllianceRequest) => {
      const response = await fetch(`${API_BASE}/world/${worldId}/alliance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!response.ok) throw await parseErrorResponse(response, 'form alliance');
      const data = await response.json();
      return AllianceResponseSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.diplomacy(worldId) });
    },
  });
}

export function useTransferTerritory(worldId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: TransferTerritoryRequest) => {
      const response = await fetch(`${API_BASE}/world/${worldId}/transfer-territory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });
      if (!response.ok) throw await parseErrorResponse(response, 'transfer territory');
      const data = await response.json();
      return TerritoryTransferResponseSchema.parse(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.territories(worldId) });
      queryClient.invalidateQueries({ queryKey: geopoliticsKeys.resources(worldId) });
    },
  });
}
