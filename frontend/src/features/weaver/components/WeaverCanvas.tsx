/**
 * WeaverCanvas - Main React Flow canvas for story weaving
 */
import { useMemo } from 'react';
import { ReactFlow, Background, Controls, MiniMap, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes, type CharacterNodeData } from './nodes';
import { edgeTypes } from './edges';
import {
  useWeaverEdges,
  useWeaverNodes,
  useWeaverOnConnect,
  useWeaverOnEdgesChange,
  useWeaverOnNodesChange,
  useWeaverFilteredPlotlineId,
} from '../store/weaverStore';
import type { SceneNodeData } from '../types';
import { useForeshadowings } from '@/features/director/api/foreshadowingApi';
import { foreshadowingsToEdges } from '../utils/foreshadowingUtils';

// Tailwind color palette values for React Flow API
export const FLOW_COLORS = {
  zinc: 'hsl(var(--muted-foreground))',
  red: 'hsl(var(--destructive))',
  blue: 'hsl(var(--primary))',
  green: 'hsl(var(--success))',
  purple: 'hsl(var(--accent))',
  orange: 'hsl(var(--warning))',
  background: 'hsl(var(--border))',
  minimapMask: 'hsl(var(--foreground) / 0.08)',
} as const;

function getNodeColor(node: Node): string {
  const nodeData = node.data as CharacterNodeData | undefined;

  if (node.type === 'world') return FLOW_COLORS.purple;
  if (node.type === 'faction') return FLOW_COLORS.orange;
  if (node.type === 'location') return FLOW_COLORS.green;
  if (node.type === 'event') return FLOW_COLORS.orange;
  if (node.type === 'scene') return FLOW_COLORS.purple;

  // Character node colors based on role
  switch (nodeData?.role) {
    case 'Protagonist':
      return FLOW_COLORS.blue;
    case 'Antagonist':
      return FLOW_COLORS.red;
    case 'Mentor':
      return FLOW_COLORS.green;
    default:
      return FLOW_COLORS.zinc;
  }
}
/**
 * Check if a scene node belongs to the filtered plotline (DIR-051)
 */
function sceneMatchesPlotline(node: Node, filteredPlotlineId: string | null): boolean {
  if (node.type !== 'scene' || !filteredPlotlineId) {
    return true;
  }
  const sceneData = node.data as SceneNodeData;
  return sceneData.plotlines?.some((p) => p.id === filteredPlotlineId) ?? false;
}

/**
 * Apply dimming to nodes that don't match the plotline filter
 * Non-matching nodes get opacity 30%, matching nodes remain at full opacity
 */
function applyPlotlineFilterToNodes(
  nodes: Node[],
  filteredPlotlineId: string | null
): Node[] {
  if (!filteredPlotlineId) {
    return nodes;
  }
  return nodes.map((node) => ({
    ...node,
    style: {
      ...node.style,
      opacity: sceneMatchesPlotline(node, filteredPlotlineId) ? 1 : 0.3,
    },
  }));
}

/**
 * Apply dimming to edges based on filtered plotline
 * - Edges between filtered scenes remain visible
 * - Edges where either endpoint is not in the filter are dimmed
 * - Non-scene nodes (character, location, etc.) are not affected by filter
 */
function applyPlotlineFilterToEdges(
  edges: Edge[],
  nodes: Node[],
  filteredPlotlineId: string | null
): Edge[] {
  if (!filteredPlotlineId) {
    return edges;
  }

  return edges.map((edge) => {
    const sourceNode = nodes.find((n) => n.id === edge.source);
    const targetNode = nodes.find((n) => n.id === edge.target);

    const sourceMatches = sourceNode ? sceneMatchesPlotline(sourceNode, filteredPlotlineId) : true;
    const targetMatches = targetNode ? sceneMatchesPlotline(targetNode, filteredPlotlineId) : true;

    // Dim the edge if either endpoint doesn't match the filter
    const shouldDim = !sourceMatches || !targetMatches;

    return {
      ...edge,
      style: {
        ...edge.style,
        opacity: shouldDim ? 0.3 : 1,
      },
    };
  });
}

export function WeaverCanvas() {
  const nodes = useWeaverNodes();
  const edges = useWeaverEdges();
  const onNodesChange = useWeaverOnNodesChange();
  const onEdgesChange = useWeaverOnEdgesChange();
  const onConnect = useWeaverOnConnect();
  const filteredPlotlineId = useWeaverFilteredPlotlineId();

  // Fetch foreshadowings for visual connections (DIR-053)
  const { data: foreshadowingsData } = useForeshadowings();
  const foreshadowings = foreshadowingsData?.foreshadowings || [];

  // Apply plotline filtering to nodes and edges
  const filteredNodes = useMemo(
    () => applyPlotlineFilterToNodes(nodes, filteredPlotlineId),
    [nodes, filteredPlotlineId]
  );

  const filteredEdges = useMemo(
    () => applyPlotlineFilterToEdges(edges, nodes, filteredPlotlineId),
    [edges, nodes, filteredPlotlineId]
  );

  // Create foreshadowing edges (DIR-053)
  const foreshadowingEdges = useMemo(
    () => foreshadowingsToEdges(foreshadowings),
    [foreshadowings]
  );

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <ReactFlow
      nodes={filteredNodes}
      edges={[...filteredEdges, ...foreshadowingEdges]}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      proOptions={proOptions}
      fitView
      data-testid="weaver-canvas"
      className="bg-weaver-canvas"
    >
      <Background color={FLOW_COLORS.background} gap={16} />
      <Controls className="!border-weaver-border !bg-weaver-surface !shadow-md" />
      <MiniMap
        nodeColor={getNodeColor}
        className="!border-weaver-border !bg-weaver-surface !shadow-md"
        maskColor={FLOW_COLORS.minimapMask}
      />
    </ReactFlow>
  );
}
