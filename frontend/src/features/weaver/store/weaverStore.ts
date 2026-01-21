/**
 * Weaver Store - Centralized React Flow state for Weaver
 */
import { create } from 'zustand';
import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type Node,
  type OnEdgesChange,
  type OnNodesChange,
} from '@xyflow/react';
import type { OrchestrationStartRequest } from '@/shared/types/orchestration';
import type { CharacterNodeData } from '../components/nodes/CharacterNode';
import type { EventNodeData } from '../components/nodes/EventNode';
import type { LocationNodeData } from '../components/nodes/LocationNode';

type WeaverNodeData = CharacterNodeData | EventNodeData | LocationNodeData;
type WeaverNode = Node<WeaverNodeData>;

type WeaverState = {
  nodes: WeaverNode[];
  edges: Edge[];
  startParams: Pick<OrchestrationStartRequest, 'total_turns' | 'setting' | 'scenario'>;
  setNodes: (nodes: WeaverNode[]) => void;
  setEdges: (edges: Edge[]) => void;
  setStartParams: (params: Partial<WeaverState['startParams']>) => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: (connection: Connection) => void;
  addNode: (node: WeaverNode) => void;
  getOrchestrationStartRequest: () => OrchestrationStartRequest;
};

const defaultNodes: WeaverNode[] = [
  {
    id: '1',
    type: 'character',
    position: { x: 250, y: 50 },
    data: {
      name: 'Alice',
      role: 'Protagonist',
      traits: ['Brave', 'Curious', 'Kind'],
    },
  },
  {
    id: '2',
    type: 'character',
    position: { x: 100, y: 250 },
    data: {
      name: 'Bob',
      role: 'Mentor',
      traits: ['Wise', 'Patient'],
    },
  },
  {
    id: '3',
    type: 'character',
    position: { x: 400, y: 250 },
    data: {
      name: 'Carol',
      role: 'Antagonist',
      traits: ['Cunning', 'Ambitious'],
    },
  },
];

const defaultEdges: Edge[] = [
  {
    id: 'e1-2',
    source: '1',
    target: '2',
    label: 'learns from',
    animated: true,
    style: { stroke: 'hsl(var(--muted-foreground))' },
  },
  {
    id: 'e1-3',
    source: '1',
    target: '3',
    label: 'rivals',
    style: { stroke: 'hsl(var(--destructive))' },
  },
];

const buildOrchestrationStartRequest = (
  nodes: WeaverNode[],
  overrides: WeaverState['startParams']
): OrchestrationStartRequest => {
  const character_names = nodes
    .filter((node) => node.type === 'character')
    .map((node) => (node.data as CharacterNodeData).name)
    .filter((name) => typeof name === 'string' && name.length > 0);

  const settingNode = nodes.find((node) => node.type === 'location');
  const scenarioNode = nodes.find((node) => node.type === 'event');

  return {
    character_names,
    total_turns: overrides.total_turns,
    setting: overrides.setting ?? (settingNode?.data as LocationNodeData | undefined)?.name,
    scenario: overrides.scenario ?? (scenarioNode?.data as EventNodeData | undefined)?.title,
  };
};

export const useWeaverStore = create<WeaverState>((set, get) => ({
  nodes: defaultNodes,
  edges: defaultEdges,
  startParams: {
    total_turns: 3,
    setting: undefined,
    scenario: undefined,
  },
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setStartParams: (params) =>
    set((state) => ({ startParams: { ...state.startParams, ...params } })),
  onNodesChange: (changes) =>
    set((state) => ({ nodes: applyNodeChanges(changes, state.nodes) })),
  onEdgesChange: (changes) =>
    set((state) => ({ edges: applyEdgeChanges(changes, state.edges) })),
  onConnect: (connection) =>
    set((state) => ({
      edges: addEdge(
        { ...connection, animated: true, style: { stroke: 'hsl(var(--primary))' } },
        state.edges
      ),
    })),
  addNode: (node) => set((state) => ({ nodes: [...state.nodes, node] })),
  getOrchestrationStartRequest: () =>
    buildOrchestrationStartRequest(get().nodes, get().startParams),
}));

export const useWeaverNodes = () => useWeaverStore((state) => state.nodes);
export const useWeaverEdges = () => useWeaverStore((state) => state.edges);
export const useWeaverOnNodesChange = () => useWeaverStore((state) => state.onNodesChange);
export const useWeaverOnEdgesChange = () => useWeaverStore((state) => state.onEdgesChange);
export const useWeaverOnConnect = () => useWeaverStore((state) => state.onConnect);
export const useWeaverAddNode = () => useWeaverStore((state) => state.addNode);
export const useWeaverStartParams = () => useWeaverStore((state) => state.startParams);
export const useWeaverOrchestrationRequest = () =>
  useWeaverStore((state) => state.getOrchestrationStartRequest());
export const useWeaverNodeCount = () => useWeaverStore((state) => state.nodes.length);
export const useWeaverEdgeCount = () => useWeaverStore((state) => state.edges.length);

if ((import.meta.env.DEV || import.meta.env.VITE_E2E_EXPOSE_WEAVER === 'true') && typeof window !== 'undefined') {
  (window as { __weaverStore?: typeof useWeaverStore }).__weaverStore = useWeaverStore;
}
