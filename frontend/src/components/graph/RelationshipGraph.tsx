/**
 * RelationshipGraph - React Flow graph visualization for character relationships
 *
 * Why: Provides an interactive graph view for visualizing relationships between
 * world entities (characters, locations, factions). Uses @xyflow/react for
 * performance and rich interaction patterns.
 */
import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Edge,
  type NodeTypes,
  type OnConnect,
  addEdge,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { CharacterNode, type CharacterNodeType } from './nodes/CharacterNode';

/** Dummy data for initial development - 3 test characters with 2 edges */
const initialNodes: CharacterNodeType[] = [
  {
    id: 'char-1',
    type: 'character',
    position: { x: 100, y: 100 },
    data: {
      name: 'Aria Shadowmend',
      archetype: 'Protagonist',
    },
  },
  {
    id: 'char-2',
    type: 'character',
    position: { x: 400, y: 100 },
    data: {
      name: 'Lord Vexar',
      archetype: 'Antagonist',
    },
  },
  {
    id: 'char-3',
    type: 'character',
    position: { x: 250, y: 300 },
    data: {
      name: 'Finn the Bard',
      archetype: 'Mentor',
    },
  },
];

const initialEdges: Edge[] = [
  {
    id: 'edge-1-3',
    source: 'char-1',
    target: 'char-3',
    label: 'Mentorship',
    type: 'smoothstep',
    animated: false,
    style: { stroke: 'hsl(var(--primary))', strokeWidth: 2 },
    labelStyle: { fill: 'hsl(var(--foreground))', fontWeight: 500 },
    labelBgStyle: { fill: 'hsl(var(--background))', fillOpacity: 0.9 },
  },
  {
    id: 'edge-1-2',
    source: 'char-1',
    target: 'char-2',
    label: 'Rivalry',
    type: 'smoothstep',
    animated: true,
    style: { stroke: 'hsl(var(--destructive))', strokeWidth: 2 },
    labelStyle: { fill: 'hsl(var(--foreground))', fontWeight: 500 },
    labelBgStyle: { fill: 'hsl(var(--background))', fillOpacity: 0.9 },
  },
];

/** Custom node types registry - typed to match CharacterNodeType */
const nodeTypes = {
  character: CharacterNode,
} satisfies NodeTypes;

export interface RelationshipGraphProps {
  /** Optional CSS class name */
  className?: string;
}

/**
 * RelationshipGraph renders an interactive node graph for entity relationships.
 * Currently displays dummy data for development verification.
 */
export function RelationshipGraph({ className }: RelationshipGraphProps) {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect: OnConnect = useCallback(
    (connection) => {
      setEdges((eds) => addEdge(connection, eds));
    },
    [setEdges]
  );

  /** Theme-aware colors for MiniMap */
  const minimapStyle = useMemo(
    () => ({
      backgroundColor: 'hsl(var(--card))',
    }),
    []
  );

  return (
    <div className={className} data-testid="relationship-graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        className="rounded-lg border border-border bg-card"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color="hsl(var(--muted-foreground) / 0.3)"
        />
        <Controls
          className="!rounded-md !border-border !bg-card !shadow-md"
          showInteractive={false}
        />
        <MiniMap
          style={minimapStyle}
          nodeColor="hsl(var(--primary))"
          maskColor="hsl(var(--background) / 0.8)"
          className="!rounded-md !border-border"
        />
      </ReactFlow>
    </div>
  );
}

export default RelationshipGraph;
