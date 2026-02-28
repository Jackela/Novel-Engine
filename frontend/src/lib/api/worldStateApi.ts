/**
 * World State API Hooks using TanStack Query (PREP-011)
 *
 * Provides type-safe access to World State endpoints for
 * geopolitical visualization: territories, diplomacy, and resources.
 */
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

// ============ Types ============

export interface TerritorySummary {
  location_id: string;
  name: string;
  location_type: string;
  controlling_faction_id: string | null;
  contested_by: string[];
  territory_value: number;
  infrastructure_level: number;
  population: number;
  resource_types: string[];
}

export interface TerritoriesResponse {
  world_id: string;
  territories: TerritorySummary[];
  total_count: number;
  controlled_count: number;
  contested_count: number;
}

export interface FactionResourceSummary {
  faction_id: string;
  faction_name: string;
  resources: Record<string, number>;
  total_territories: number;
  total_population: number;
}

export interface WorldResourcesResponse {
  world_id: string;
  factions: FactionResourceSummary[];
  total_resources: Record<string, number>;
  timestamp: string;
}

export interface PactSummary {
  pact_id: string;
  faction_a_id: string;
  faction_b_id: string;
  pact_type: string;
  signed_date: string | null;
  expires_date: string | null;
  is_active: boolean;
}

export interface DiplomacyMatrixDetailResponse {
  world_id: string;
  matrix: Record<string, Record<string, string>>;
  factions: string[];
  active_pacts: PactSummary[];
}

// ============ Query Keys ============

/**
 * Query key factory for world state.
 * Why: Centralizes key creation for consistent cache management.
 */
const worldStateKeys = {
  all: ['worldState'] as const,
  territories: (worldId: string) =>
    [...worldStateKeys.all, 'territories', worldId] as const,
  resources: (worldId: string) =>
    [...worldStateKeys.all, 'resources', worldId] as const,
  diplomacy: (worldId: string) =>
    [...worldStateKeys.all, 'diplomacy', worldId] as const,
};

// ============ Raw API Functions ============

/**
 * Get territories with control information for a world.
 */
async function getTerritories(worldId: string): Promise<TerritoriesResponse> {
  return api.get<TerritoriesResponse>(`/world/${worldId}/territories`);
}

/**
 * Get resource summary for all factions in a world.
 */
async function getWorldResources(
  worldId: string
): Promise<WorldResourcesResponse> {
  return api.get<WorldResourcesResponse>(`/world/${worldId}/resources`);
}

/**
 * Get diplomacy matrix with pacts for a world.
 */
async function getDiplomacyDetail(
  worldId: string
): Promise<DiplomacyMatrixDetailResponse> {
  return api.get<DiplomacyMatrixDetailResponse>(`/world/${worldId}/diplomacy`);
}

// ============ TanStack Query Hooks ============

/**
 * Hook to fetch territories with control information.
 *
 * @param worldId - The unique identifier for the world
 * @returns Query result with territories data
 *
 * @example
 * ```tsx
 * function TerritoryMap({ worldId }: { worldId: string }) {
 *   const { data, isLoading } = useTerritories(worldId);
 *
 *   if (isLoading) return <Spinner />;
 *
 *   return (
 *     <div>
 *       {data?.territories.map(t => (
 *         <TerritoryCard key={t.location_id} territory={t} />
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 */
export function useTerritories(worldId: string | undefined) {
  return useQuery({
    queryKey: worldStateKeys.territories(worldId ?? ''),
    queryFn: () => getTerritories(worldId!),
    enabled: !!worldId,
    staleTime: 30000, // 30 seconds - territories don't change rapidly
  });
}

/**
 * Hook to fetch faction resource summary.
 *
 * @param worldId - The unique identifier for the world
 * @returns Query result with resources data
 *
 * @example
 * ```tsx
 * function ResourceDashboard({ worldId }: { worldId: string }) {
 *   const { data } = useWorldResources(worldId);
 *
 *   return (
 *     <div>
 *       {data?.factions.map(f => (
 *         <FactionResourceCard key={f.faction_id} faction={f} />
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 */
export function useWorldResources(worldId: string | undefined) {
  return useQuery({
    queryKey: worldStateKeys.resources(worldId ?? ''),
    queryFn: () => getWorldResources(worldId!),
    enabled: !!worldId,
    staleTime: 60000, // 1 minute - resources change slowly
  });
}

/**
 * Hook to fetch diplomacy matrix with pacts.
 *
 * @param worldId - The unique identifier for the world
 * @returns Query result with diplomacy data including pacts
 *
 * @example
 * ```tsx
 * function DiplomacyView({ worldId }: { worldId: string }) {
 *   const { data } = useDiplomacyDetail(worldId);
 *
 *   return (
 *     <DiplomacyGrid
 *       matrix={data?.matrix ?? {}}
 *       factions={data?.factions ?? []}
 *       pacts={data?.active_pacts ?? []}
 *     />
 *   );
 * }
 * ```
 */
export function useDiplomacyDetail(worldId: string | undefined) {
  return useQuery({
    queryKey: worldStateKeys.diplomacy(worldId ?? ''),
    queryFn: () => getDiplomacyDetail(worldId!),
    enabled: !!worldId,
    staleTime: 30000, // 30 seconds
  });
}

// ============ Utility Functions ============

/**
 * Generate a consistent color for a faction based on its ID.
 * Uses hash-based color generation for deterministic colors.
 *
 * @param factionId - The faction ID to generate a color for
 * @returns HSL color string
 */
export function getFactionColor(factionId: string | null | undefined): string {
  if (!factionId) {
    return 'hsl(0, 0%, 60%)'; // Gray for uncontrolled
  }

  // Hash the faction ID to get consistent hue
  let hash = 0;
  for (let i = 0; i < factionId.length; i++) {
    hash = factionId.charCodeAt(i) + ((hash << 5) - hash);
    hash = hash & hash; // Convert to 32-bit integer
  }

  // Map to hue (0-360), use consistent saturation and lightness
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 45%)`;
}

/**
 * Get background color class for a faction.
 *
 * @param factionId - The faction ID
 * @returns CSS color string
 */
export function getFactionBgColor(factionId: string | null | undefined): string {
  return getFactionColor(factionId);
}

/**
 * Get border color for a faction (lighter version).
 *
 * @param factionId - The faction ID
 * @returns CSS color string (lighter than bg)
 */
export function getFactionBorderColor(
  factionId: string | null | undefined
): string {
  if (!factionId) {
    return 'hsl(0, 0%, 70%)';
  }

  let hash = 0;
  for (let i = 0; i < factionId.length; i++) {
    hash = factionId.charCodeAt(i) + ((hash << 5) - hash);
    hash = hash & hash;
  }

  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 65%)`;
}

// Export raw functions for non-hook usage
export { getTerritories, getWorldResources, getDiplomacyDetail };

// ============ Aliases for backward compatibility ============

/**
 * Alias for useDiplomacyDetail for consistency with API naming.
 * PREP-012: Used by DiplomacyGrid component.
 */
export const useDiplomacyMatrix = useDiplomacyDetail;
