/**
 * useWorldGeneration - Hook for generating world settings and visualizing as graph nodes
 */
import { useMutation } from '@tanstack/react-query';
import { generateWorld } from '@/lib/api';
import { generateId } from '@/lib/utils';
import type {
  WorldGenerationRequest,
  WorldGenerationResponse,
} from '@/types/schemas';
import type { WorldNodeData } from '../components/nodes/WorldNode';
import type { FactionNodeData } from '../components/nodes/FactionNode';
import type { LocationNodeData } from '../components/nodes/LocationNode';
import {
  useWeaverAddNode,
  useWeaverStore,
  useWeaverUpdateNode,
  type WeaverNode,
} from '../store/weaverStore';

export type WorldMutationContext = {
  worldNodeId: string;
  loadingNodeId: string;
};

/**
 * Calculate hierarchical auto-layout positions for world graph nodes
 * Layout: World at top center, factions in middle row, locations at bottom
 */
function calculateAutoLayoutPositions(
  factionCount: number,
  locationCount: number,
  existingNodes: WeaverNode[]
): {
  worldPosition: { x: number; y: number };
  factionPositions: { x: number; y: number }[];
  locationPositions: { x: number; y: number }[];
} {
  // Find rightmost existing node to place new nodes after
  const maxExistingX = existingNodes.reduce(
    (max, node) => Math.max(max, node.position.x),
    0
  );
  const baseX = maxExistingX > 0 ? maxExistingX + 400 : 400;

  const rowSpacing = 200;
  const nodeSpacing = 280;

  // World node at top center
  const worldPosition = { x: baseX, y: 50 };

  // Factions in middle row, centered under world
  const factionStartX = baseX - ((factionCount - 1) * nodeSpacing) / 2;
  const factionPositions = Array.from({ length: factionCount }, (_, i) => ({
    x: factionStartX + i * nodeSpacing,
    y: 50 + rowSpacing,
  }));

  // Locations at bottom row, centered
  const locationStartX = baseX - ((locationCount - 1) * nodeSpacing) / 2;
  const locationPositions = Array.from({ length: locationCount }, (_, i) => ({
    x: locationStartX + i * nodeSpacing,
    y: 50 + rowSpacing * 2,
  }));

  return { worldPosition, factionPositions, locationPositions };
}

/**
 * Create a loading placeholder node while world is generating
 */
function createLoadingNode(existingNodes: WeaverNode[]): WeaverNode {
  const maxX = existingNodes.reduce((max, n) => Math.max(max, n.position.x), 0);
  const data: WorldNodeData = {
    name: 'Generating World...',
    description: 'Creating factions, locations, and history',
    genre: 'loading',
    era: '',
    tone: '',
    themes: [],
    magic_level: 0,
    technology_level: 0,
    status: 'loading',
  };

  return {
    id: generateId('world-loading'),
    type: 'world',
    position: { x: maxX > 0 ? maxX + 400 : 400, y: 50 },
    data,
  };
}

/**
 * Create nodes from world generation response
 */
function createWorldGraphNodes(
  response: WorldGenerationResponse,
  existingNodes: WeaverNode[]
): WeaverNode[] {
  const { worldPosition, factionPositions, locationPositions } =
    calculateAutoLayoutPositions(
      response.factions.length,
      response.locations.length,
      existingNodes
    );

  const nodes: WeaverNode[] = [];

  // World setting node
  const worldData: WorldNodeData = {
    name: response.world_setting.name,
    description: response.world_setting.description,
    genre: response.world_setting.genre,
    era: response.world_setting.era,
    tone: response.world_setting.tone,
    themes: response.world_setting.themes,
    magic_level: response.world_setting.magic_level,
    technology_level: response.world_setting.technology_level,
    status: 'idle',
  };

  nodes.push({
    id: response.world_setting.id,
    type: 'world',
    position: worldPosition,
    data: worldData,
  });

  // Faction nodes
  response.factions.forEach((faction, index) => {
    const factionData: FactionNodeData = {
      name: faction.name,
      description: faction.description,
      faction_type: faction.faction_type,
      alignment: faction.alignment,
      values: faction.values,
      goals: faction.goals,
      influence: faction.influence,
      ally_count: faction.ally_count,
      enemy_count: faction.enemy_count,
      status: 'idle',
    };

    const position = factionPositions[index] ?? { x: 400 + index * 280, y: 250 };
    nodes.push({
      id: faction.id,
      type: 'faction',
      position,
      data: factionData,
    });
  });

  // Location nodes (using existing LocationNode type)
  response.locations.forEach((location, index) => {
    // Map backend location_type to frontend LocationNode type
    const typeMap: Record<string, LocationNodeData['type']> = {
      city: 'city',
      capital: 'city',
      town: 'city',
      village: 'city',
      port: 'city',
      fortress: 'building',
      castle: 'building',
      temple: 'building',
      dungeon: 'dungeon',
      cave: 'dungeon',
      ruins: 'dungeon',
      forest: 'wilderness',
      mountain: 'wilderness',
      desert: 'wilderness',
      swamp: 'wilderness',
      plains: 'wilderness',
      ocean: 'wilderness',
      river: 'wilderness',
      island: 'wilderness',
    };

    const locationType = typeMap[location.location_type] ?? 'other';

    const locationData: LocationNodeData = {
      name: location.name,
      type: locationType,
      description: location.description,
      status: 'idle',
    };

    const position = locationPositions[index] ?? { x: 400 + index * 280, y: 450 };
    nodes.push({
      id: location.id,
      type: 'location',
      position,
      data: locationData,
    });
  });

  return nodes;
}

export function useWorldGeneration() {
  const addNode = useWeaverAddNode();
  const updateNode = useWeaverUpdateNode();

  return useMutation({
    mutationFn: generateWorld,
    onMutate: async (_input: WorldGenerationRequest) => {
      const existingNodes = useWeaverStore.getState().nodes;
      const loadingNode = createLoadingNode(existingNodes);
      addNode(loadingNode);
      return {
        worldNodeId: '',
        loadingNodeId: loadingNode.id,
      } satisfies WorldMutationContext;
    },
    onSuccess: (response, _variables, context) => {
      if (!context) return;

      // Remove loading node
      const store = useWeaverStore.getState();
      store.setNodes(store.nodes.filter((n) => n.id !== context.loadingNodeId));

      // Get current nodes (without the loading node we just removed)
      const currentNodes = useWeaverStore.getState().nodes;

      // Create and add all world graph nodes
      const newNodes = createWorldGraphNodes(response, currentNodes);
      newNodes.forEach((node) => addNode(node));
    },
    onError: (error, _variables, context) => {
      if (!context?.loadingNodeId) return;
      const message = error instanceof Error ? error.message : 'World generation failed';
      updateNode(context.loadingNodeId, (node) => {
        const updatedData = {
          ...(node.data as WorldNodeData),
          name: 'Generation Failed',
          description: message,
          status: 'error' as const,
          errorMessage: message,
        };
        return { ...node, data: updatedData };
      });
    },
  });
}
