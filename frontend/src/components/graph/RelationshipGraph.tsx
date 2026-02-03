/**
 * RelationshipGraph - React Flow graph visualization for character relationships
 *
 * Why: Provides an interactive graph view for visualizing relationships between
 * world entities (characters, locations, factions). Uses @xyflow/react for
 * performance and rich interaction patterns. Dagre layout provides automatic
 * node positioning for readable graph structures.
 */
import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Edge,
  type Node,
  type NodeProps,
  type NodeTypes,
  BackgroundVariant,
  type OnSelectionChangeFunc,
} from '@xyflow/react';
import { X, Users, Sparkles, Loader2, User } from 'lucide-react';
import '@xyflow/react/dist/style.css';

import { RelationshipStatusBars } from './RelationshipStatusBars';
import { Button, Badge } from '@/shared/components/ui';
import type {
  CharacterSummary,
  RelationshipResponse,
  RelationshipType,
} from '@/types/schemas';
import { cn } from '@/lib/utils';
import { generateRelationshipHistory } from '@/lib/api';

/**
 * Simple character node data for relationship graph display
 */
interface SimpleCharacterNodeData extends Record<string, unknown> {
  name: string;
  archetype?: string;
  avatarUrl?: string;
}

type SimpleCharacterNodeType = Node<SimpleCharacterNodeData>;

/**
 * SimpleCharacterNode - Minimal character node for relationship graph
 *
 * Why: Displays a compact character node with name and archetype badge,
 * optimized for the relationship graph layout.
 */
function SimpleCharacterNodeComponent({
  data,
  selected,
}: NodeProps<SimpleCharacterNodeType>) {
  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2 !w-2 !rounded-full !border-2 !border-primary !bg-background"
      />

      <div
        className={cn(
          'min-w-[140px] rounded-lg border bg-card p-3 shadow-md transition-all',
          'hover:shadow-lg',
          selected
            ? 'border-primary ring-2 ring-primary ring-offset-2 ring-offset-background'
            : 'border-border'
        )}
      >
        <div className="flex items-center gap-3">
          {/* Avatar placeholder */}
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
            {data.avatarUrl ? (
              <img
                src={data.avatarUrl}
                alt={data.name}
                className="h-full w-full rounded-full object-cover"
              />
            ) : (
              <User className="h-5 w-5 text-muted-foreground" />
            )}
          </div>

          <div className="min-w-0 flex-1">
            {/* Character name */}
            <p className="truncate text-sm font-medium text-foreground">{data.name}</p>

            {/* Archetype badge */}
            {data.archetype && (
              <Badge variant="secondary" className="mt-1 text-[10px]">
                {data.archetype}
              </Badge>
            )}
          </div>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2 !w-2 !rounded-full !border-2 !border-primary !bg-background"
      />
    </>
  );
}

const SimpleCharacterNode = memo(SimpleCharacterNodeComponent);

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

/** Custom node types registry - typed to match SimpleCharacterNodeType */
const nodeTypes = {
  character: SimpleCharacterNode,
} satisfies NodeTypes;

type DagreGraph = {
  setDefaultEdgeLabel: (value: () => unknown) => DagreGraph;
  setGraph: (config: {
    rankdir: 'TB' | 'LR';
    nodesep: number;
    ranksep: number;
    marginx: number;
    marginy: number;
  }) => void;
  setNode: (id: string, size: { width: number; height: number }) => void;
  setEdge: (source: string, target: string) => void;
  node: (id: string) => { x: number; y: number };
};

type DagreApi = {
  graphlib: {
    Graph: new (...args: unknown[]) => DagreGraph;
  };
  layout: (graph: DagreGraph) => void;
};

let dagreLoader: Promise<DagreApi | null> | null = null;

async function loadDagre(): Promise<DagreApi | null> {
  if (!dagreLoader) {
    dagreLoader = import('@dagrejs/dagre')
      .then((mod) => {
        const module = mod as unknown as { default?: DagreApi };
        return module.default ?? (mod as unknown as DagreApi);
      })
      .catch((error) => {
        console.warn(
          'RelationshipGraph: Dagre unavailable, falling back to grid layout.',
          error
        );
        return null;
      });
  }
  return dagreLoader;
}

function applyFallbackLayout(
  nodes: SimpleCharacterNodeType[]
): SimpleCharacterNodeType[] {
  const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
  const gapX = 220;
  const gapY = 140;

  return nodes.map((node, index) => ({
    ...node,
    position: {
      x: (index % columns) * gapX,
      y: Math.floor(index / columns) * gapY,
    },
  }));
}

/**
 * Apply Dagre layout to nodes and edges.
 * Why: Automatic layout ensures readable graphs without manual positioning.
 * Uses 'TB' (top-bottom) direction for intuitive hierarchy visualization.
 */
function applyDagreLayout(
  nodes: SimpleCharacterNodeType[],
  edges: Edge[],
  dagre: DagreApi | null,
  direction: 'TB' | 'LR' = 'TB'
): SimpleCharacterNodeType[] {
  if (!dagre) {
    return applyFallbackLayout(nodes);
  }

  const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

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

  try {
    dagre.layout(g);
  } catch (error) {
    console.warn(
      'RelationshipGraph: Dagre layout failed, using fallback layout.',
      error
    );
    return applyFallbackLayout(nodes);
  }

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

/** Extended edge data including relationship metrics */
interface RelationshipEdgeData extends Record<string, unknown> {
  relationshipType: RelationshipType;
  strength: number;
  trust: number;
  romance: number;
  description: string;
  sourceName: string;
  targetName: string;
}

/**
 * Convert API data to React Flow nodes and edges.
 */
function transformDataToGraph(
  characters: CharacterSummary[],
  relationships: RelationshipResponse[],
  dagre: DagreApi | null
): { nodes: SimpleCharacterNodeType[]; edges: Edge<RelationshipEdgeData>[] } {
  // Create a map for quick character lookup
  const characterMap = new Map(characters.map((c) => [c.id, c]));

  // Create a set of character IDs that are involved in relationships
  const involvedCharacterIds = new Set<string>();
  relationships.forEach((rel) => {
    involvedCharacterIds.add(rel.source_id);
    involvedCharacterIds.add(rel.target_id);
  });

  // Create nodes only for characters involved in relationships
  const nodes: SimpleCharacterNodeType[] = characters
    .filter((char) => involvedCharacterIds.has(char.id))
    .map((char) => {
      const data: SimpleCharacterNodeData = {
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

  // Create edges from relationships with extended data
  const edges: Edge<RelationshipEdgeData>[] = relationships.map((rel) => ({
    id: rel.id,
    source: rel.source_id,
    target: rel.target_id,
    label: getRelationshipLabel(rel.relationship_type),
    type: 'smoothstep',
    animated: getEdgeAnimated(rel.relationship_type),
    style: getEdgeStyle(rel.relationship_type, rel.strength),
    labelStyle: { fill: 'hsl(var(--foreground))', fontWeight: 500, fontSize: 11 },
    labelBgStyle: { fill: 'hsl(var(--background))', fillOpacity: 0.9 },
    data: {
      relationshipType: rel.relationship_type,
      strength: rel.strength,
      trust: rel.trust,
      romance: rel.romance,
      description: rel.description,
      sourceName: characterMap.get(rel.source_id)?.name ?? 'Unknown',
      targetName: characterMap.get(rel.target_id)?.name ?? 'Unknown',
    },
  }));

  // Apply dagre layout
  const layoutedNodes = applyDagreLayout(nodes, edges, dagre);

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
 * Fetches character and relationship data from the API. Clicking an edge shows
 * detailed relationship metrics with Trust and Romance status bars.
 */
export function RelationshipGraph({ className, onNodeSelect }: RelationshipGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<SimpleCharacterNodeType>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge<RelationshipEdgeData>>(
    []
  );
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge<RelationshipEdgeData> | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGeneratingHistory, setIsGeneratingHistory] = useState(false);
  const [generatedBackstory, setGeneratedBackstory] = useState<string | null>(null);
  const [dagreApi, setDagreApi] = useState<DagreApi | null>(null);

  useEffect(() => {
    let isMounted = true;
    void loadDagre().then((module) => {
      if (isMounted) {
        setDagreApi(module);
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

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
          relationshipsData.relationships || [],
          dagreApi
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
  }, [setNodes, setEdges, dagreApi]);

  useEffect(() => {
    if (!dagreApi || nodes.length === 0) {
      return;
    }
    setNodes((currentNodes) => applyDagreLayout(currentNodes, edges, dagreApi));
  }, [dagreApi, edges, nodes.length, setNodes]);

  /** Handle node selection changes */
  const onSelectionChange: OnSelectionChangeFunc = useCallback(
    ({ nodes: selectedNodes, edges: selectedEdges }) => {
      // Handle node selection
      const selected = selectedNodes.length > 0 ? (selectedNodes[0]?.id ?? null) : null;
      setSelectedNodeId(selected);
      onNodeSelect?.(selected);

      // Handle edge selection
      if (selectedEdges.length > 0) {
        const edge = selectedEdges[0] as Edge<RelationshipEdgeData>;
        setSelectedEdge(edge);
      } else if (selectedNodes.length === 0) {
        // Only clear edge when nothing is selected
        setSelectedEdge(null);
      }
    },
    [onNodeSelect]
  );

  /** Close the relationship detail panel */
  const handleCloseDetail = useCallback(() => {
    setSelectedEdge(null);
    setGeneratedBackstory(null);
  }, []);

  /** Generate backstory for the selected relationship */
  const handleGenerateHistory = useCallback(async () => {
    if (!selectedEdge) return;

    setIsGeneratingHistory(true);
    setGeneratedBackstory(null);

    try {
      const result = await generateRelationshipHistory(selectedEdge.id);
      if (result.error) {
        console.error('History generation error:', result.error);
      }
      setGeneratedBackstory(result.backstory);

      // Update the edge data with the generated backstory
      setEdges((eds) =>
        eds.map((edge) => {
          if (edge.id === selectedEdge.id && edge.data) {
            return {
              ...edge,
              data: {
                ...edge.data,
                description: result.backstory,
              },
            };
          }
          return edge;
        })
      );

      // Also update the selectedEdge to reflect the change
      setSelectedEdge((prev) => {
        if (prev && prev.data) {
          return {
            ...prev,
            data: {
              ...prev.data,
              description: result.backstory,
            },
          };
        }
        return prev;
      });
    } catch (err) {
      console.error('Failed to generate relationship history:', err);
    } finally {
      setIsGeneratingHistory(false);
    }
  }, [selectedEdge, setEdges]);

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
            <p className="text-sm">
              Create characters and add relationships to see them here
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('relative', className)} data-testid="relationship-graph">
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
        edgesFocusable
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

      {/* Relationship Detail Panel */}
      {selectedEdge && selectedEdge.data && (
        <div
          className="absolute bottom-4 left-4 right-4 rounded-lg border border-border bg-card p-4 shadow-lg"
          data-testid="relationship-detail-panel"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-4">
              {/* Header with character names */}
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">
                  {selectedEdge.data.sourceName ?? 'Unknown'}{' '}
                  <span className="text-muted-foreground">&</span>{' '}
                  {selectedEdge.data.targetName ?? 'Unknown'}
                </span>
                <Badge
                  variant="secondary"
                  style={{
                    backgroundColor:
                      RELATIONSHIP_COLORS[selectedEdge.data.relationshipType] + '20',
                    color: RELATIONSHIP_COLORS[selectedEdge.data.relationshipType],
                  }}
                >
                  {getRelationshipLabel(selectedEdge.data.relationshipType)}
                </Badge>
              </div>

              {/* Description if available */}
              {selectedEdge.data.description && (
                <p className="text-sm text-muted-foreground">
                  {selectedEdge.data.description}
                </p>
              )}

              {/* Generate History button - shown when no description or to regenerate */}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGenerateHistory}
                  disabled={isGeneratingHistory}
                  className="gap-2"
                  data-testid="generate-history-button"
                >
                  {isGeneratingHistory ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      {selectedEdge.data.description
                        ? 'Regenerate History'
                        : 'Generate History'}
                    </>
                  )}
                </Button>
                {generatedBackstory && !isGeneratingHistory && (
                  <span className="text-xs text-muted-foreground">
                    History generated
                  </span>
                )}
              </div>

              {/* Trust and Romance bars */}
              <RelationshipStatusBars
                trust={selectedEdge.data.trust}
                romance={selectedEdge.data.romance}
              />
            </div>

            {/* Close button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={handleCloseDetail}
              aria-label="Close detail panel"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default RelationshipGraph;
