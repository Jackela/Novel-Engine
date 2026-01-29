/**
 * WeaverCanvas - Main React Flow canvas for story weaving
 */
import { useMemo } from 'react';
import { ReactFlow, Background, Controls, MiniMap, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes, type CharacterNodeData } from './nodes';
import {
  useWeaverEdges,
  useWeaverNodes,
  useWeaverOnConnect,
  useWeaverOnEdgesChange,
  useWeaverOnNodesChange,
} from '../store/weaverStore';

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
export function WeaverCanvas() {
  const nodes = useWeaverNodes();
  const edges = useWeaverEdges();
  const onNodesChange = useWeaverOnNodesChange();
  const onEdgesChange = useWeaverOnEdgesChange();
  const onConnect = useWeaverOnConnect();

  const proOptions = useMemo(() => ({ hideAttribution: true }), []);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      nodeTypes={nodeTypes}
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
