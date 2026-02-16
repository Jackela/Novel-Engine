/**
 * Foreshadowing utilities for Weaver canvas (DIR-053)
 *
 * Converts foreshadowing data into React Flow edges for visualizing
 * Chekhov's Gun connections between scenes.
 */
import type { Edge } from '@xyflow/react';
import type { ForeshadowingResponse } from '@/types/schemas';

/**
 * Convert foreshadowing data to React Flow edge
 *
 * Features:
 * - Creates curved bezier edge from setup scene to payoff scene
 * - Type is 'foreshadowing' for custom edge styling
 * - Data contains full foreshadowing response for tooltip
 * - Animated for visual prominence
 * - Hidden if payoff_scene_id is null (not yet paid off)
 */
export function foreshadowingToEdge(foreshadowing: ForeshadowingResponse): Edge | null {
  // Don't create edge if no payoff scene linked yet
  if (!foreshadowing.payoff_scene_id) {
    return null;
  }

  const edgeId = `foreshadowing-${foreshadowing.id}`;

  return {
    id: edgeId,
    source: foreshadowing.setup_scene_id,
    target: foreshadowing.payoff_scene_id,
    type: 'foreshadowing',
    animated: false, // Don't animate, dashed line is sufficient
    data: {
      foreshadowing,
    },
    // Prevent deletion through canvas (only through panel)
    deletable: false,
    // Allow selection for highlighting
    selectable: true,
  };
}

/**
 * Convert multiple foreshadowings to edges
 * Filters out null results from foreshadowings without payoffs
 */
export function foreshadowingsToEdges(foreshadowings: ForeshadowingResponse[]): Edge[] {
  return foreshadowings
    .map(foreshadowingToEdge)
    .filter((edge): edge is Edge => edge !== null);
}

/**
 * Get scene node positions for foreshadowing edges
 *
 * This helps position edges correctly when scene nodes move
 */
export function getSceneNodePositions(
  sceneIds: string[],
  nodes: { id: string; position: { x: number; y: number } }[]
): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();

  sceneIds.forEach((sceneId) => {
    const node = nodes.find((n) => n.id === sceneId);
    if (node) {
      positions.set(sceneId, node.position);
    }
  });

  return positions;
}
