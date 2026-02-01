/**
 * RelationshipGraph - React Flow graph visualization for character relationships
 *
 * Why: Provides an interactive graph view for visualizing relationships between
 * world entities (characters, locations, factions). Uses @xyflow/react for
 * performance and rich interaction patterns. Dagre layout provides automatic
 * node positioning for readable graph structures.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Edge,
  type NodeTypes,
  BackgroundVariant,
  type OnSelectionChangeFunc,
} from '@xyflow/react';
import Dagre from '@dagrejs/dagre';
import '@xyflow/react/dist/style.css';

import { CharacterNode, type CharacterNodeType, type CharacterNodeData } from './nodes/CharacterNode';
import type { CharacterSummary, RelationshipResponse, RelationshipType } from '@/types/schemas';

/**
 * Map relationship types to edge colors.
 * Why: Color coding helps users quickly understand relationship dynamics.
 * Green = positive (ally, family), Red = negative (enemy), Blue = family.
 */
const RELATIONSHIP_COLORS: Record<RelationshipType, string> = {
  ally: 'hsl(142, 76%, 36%)', // Green
  family: 'hsl(217, 91%, 60%)', // Blue
  romantic: 'hsl(327, 73%, 52%)', // Pink
  mentor: 'hsl(45, 93%, 47%)', // Amber
  enemy: 'hsl(0, 84%, 60%)', // Red
  rival: 'hsl(25, 95%, 53%)', // Orange
  member_of: 'hsl(259, 94%, 51%)', // Purple
  located_in: 'hsl(173, 58%, 39%)', // Teal
  owns: 'hsl(199, 89%, 48%)', // Sky
  created: 'hsl(280, 87%, 45%)', // Violet
  historical: 'hsl(220, 9%, 46%)', // Gray
  neutral: 'hsl(220, 14%, 71%)', // Light gray
};

/**
 * Get edge animation based on relationship type.
 * Why: Animation draws attention to active conflicts (enemy) or
 * special bonds (romantic).
 */
function getEdgeAnimated(type: RelationshipType): boolean {
  return type === 'enemy' || type === 'romantic';
}

/**
 * Get edge style based on relationship type and strength.
 */
function getEdgeStyle(type: RelationshipType, strength: number) {
  const color = RELATIONSHIP_COLORS[type];
  // Stroke width varies by strength (1-4px range)
  const strokeWidth = 1 + Math.floor(strength / 33);
  return {
    stroke: color,
    strokeWidth,
  };
}

/**
 * Get human-readable label for relationship type.
 */
function getRelationshipLabel(type: RelationshipType): string {
  const labels: Record<RelationshipType, string> = {
    ally: 'Ally',
    family: 'Family',
    romantic: 'Romantic',
    mentor: 'Mentor',
    enemy: 'Enemy',
    rival: 'Rival',
    member_of: 'Member',
    located_in: 'Located In',
    owns: 'Owns',
    created: 'Created',
    historical: 'Historical',
    neutral: 'Neutral',
  };
  return labels[type];
}

/** Custom node types registry - typed to match CharacterNodeType */
const nodeTypes = {
  character: CharacterNode,
} satisfies NodeTypes;

/**
 * Apply Dagre layout to nodes and edges.
 * Why: Automatic layout ensures readable graphs without manual positioning.
 * Uses 'TB' (top-bottom) direction for intuitive hierarchy visualization.
 */
function applyDagreLayout(
  nodes: CharacterNodeType[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
): CharacterNodeType[] {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

  g.setGraph({
    rankdir: direction,
    nodesep: 80,
    ranksep: 100,
    marginx: 20,
    marginy: 20,
  });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: 180, height: 80 });
  });

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  Dagre.layout(g);

  return nodes.map((node) => {
    const nodeWithPosition = g.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 90, // Center the node (width/2)
        y: nodeWithPosition.y - 40, // Center the node (height/2)
      },
    };
  });
}

/**
 * Convert API data to React Flow nodes and edges.
 */
function transformDataToGraph(
  characters: CharacterSummary[],
  relationships: RelationshipResponse[]
): { nodes: CharacterNodeType[]; edges: Edge[] } {
  // Create a set of character IDs that are involved in relationships
  const involvedCharacterIds = new Set<string>();
  relationships.forEach((rel) => {
    involvedCharacterIds.add(rel.source_id);
    involvedCharacterIds.add(rel.target_id);
  });

  // Create nodes only for characters involved in relationships
  const nodes: CharacterNodeType[] = characters
    .filter((char) => involvedCharacterIds.has(char.id))
    .map((char) => {
      const data: CharacterNodeData = {
        name: char.name,
      };
      if (char.archetype) {
        data.archetype = char.archetype;
      }
      return {
        id: char.id,
        type: 'character' as const,
        position: { x: 0, y: 0 }, // Will be set by dagre
        data,
      };
    });

  // Create edges from relationships
  const edges: Edge[] = relationships.map((rel) => ({
    id: rel.id,
    source: rel.source_id,
    target: rel.target_id,
    label: getRelationshipLabel(rel.relationship_type),
    type: 'smoothstep',
    animated: getEdgeAnimated(rel.relationship_type),
    style: getEdgeStyle(rel.relationship_type, rel.strength),
    labelStyle: { fill: 'hsl(var(--foreground))', fontWeight: 500, fontSize: 11 },
    labelBgStyle: { fill: 'hsl(var(--background))', fillOpacity: 0.9 },
    data: { relationshipType: rel.relationship_type, strength: rel.strength },
  }));

  // Apply dagre layout
  const layoutedNodes = applyDagreLayout(nodes, edges);

  return { nodes: layoutedNodes, edges };
}

export interface RelationshipGraphProps {
  /** Optional CSS class name */
  className?: string;
  /** Callback when a node is selected */
  onNodeSelect?: (nodeId: string | null) => void;
}

/**
 * RelationshipGraph renders an interactive node graph for entity relationships.
 * Fetches character and relationship data from the API.
 */
export function RelationshipGraph({ className, onNodeSelect }: RelationshipGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<CharacterNodeType>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const [charactersRes, relationshipsRes] = await Promise.all([
          fetch('/api/characters'),
          fetch('/api/relationships'),
        ]);

        if (!charactersRes.ok || !relationshipsRes.ok) {
          throw new Error('Failed to fetch graph data');
        }

        const charactersData = await charactersRes.json();
        const relationshipsData = await relationshipsRes.json();

        const { nodes: newNodes, edges: newEdges } = transformDataToGraph(
          charactersData.characters || [],
          relationshipsData.relationships || []
        );

        setNodes(newNodes);
        setEdges(newEdges);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [setNodes, setEdges]);

  /** Handle node selection changes */
  const onSelectionChange: OnSelectionChangeFunc = useCallback(
    ({ nodes: selectedNodes }) => {
      const selected = selectedNodes.length > 0 ? selectedNodes[0]?.id ?? null : null;
      setSelectedNodeId(selected);
      onNodeSelect?.(selected);
    },
    [onNodeSelect]
  );

  /** Theme-aware colors for MiniMap */
  const minimapStyle = useMemo(
    () => ({
      backgroundColor: 'hsl(var(--card))',
    }),
    []
  );

  if (isLoading) {
    return (
      <div className={className} data-testid="relationship-graph">
        <div className="flex h-full items-center justify-center rounded-lg border border-border bg-card">
          <div className="text-muted-foreground">Loading graph...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={className} data-testid="relationship-graph">
        <div className="flex h-full items-center justify-center rounded-lg border border-destructive/50 bg-destructive/10">
          <div className="text-destructive">{error}</div>
        </div>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className={className} data-testid="relationship-graph">
        <div className="flex h-full items-center justify-center rounded-lg border border-border bg-card">
          <div className="text-center text-muted-foreground">
            <p className="font-medium">No relationships to display</p>
            <p className="text-sm">Create characters and add relationships to see them here</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={className} data-testid="relationship-graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onSelectionChange={onSelectionChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
        className="rounded-lg border border-border bg-card"
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
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
          nodeColor={(node) => {
            if (node.id === selectedNodeId) {
              return 'hsl(var(--primary))';
            }
            return 'hsl(var(--muted-foreground))';
          }}
          maskColor="hsl(var(--background) / 0.8)"
          className="!rounded-md !border-border"
        />
      </ReactFlow>
    </div>
  );
}

export default RelationshipGraph;
