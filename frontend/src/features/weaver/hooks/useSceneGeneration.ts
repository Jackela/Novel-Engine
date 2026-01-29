import { useMutation } from '@tanstack/react-query';
import { generateScene } from '@/lib/api/sceneApi';
import { generateId } from '@/lib/utils';
import type {
  SceneGenerationRequest,
  SceneGenerationResponse,
  CharacterGenerationResponse,
} from '@/types/schemas';
import type { SceneNodeData } from '../types';
import type { CharacterNodeData } from '../components/nodes/CharacterNode';
import {
  useWeaverAddNode,
  useWeaverStore,
  useWeaverUpdateNode,
  type WeaverNode,
} from '../store/weaverStore';

export type SceneMutationContext = {
  nodeId: string;
};

export type UpdateNodeFn = (
  nodeId: string,
  updater: (node: WeaverNode) => WeaverNode
) => void;

export type SceneGenerationInput = {
  sourceNodeId: string;
  sceneType: string;
  tone?: string | undefined;
};

/**
 * Creates an optimistic scene node positioned to the right of the source character node
 * Returns null if source node is not found
 */
export const createOptimisticSceneNode = (
  sourceNodeId: string,
  sceneType: string
): { node: WeaverNode; edge: { id: string; source: string; target: string; animated: boolean; style: { stroke: string } } } | null => {
  const sourceNode = useWeaverStore.getState().nodes.find(
    (n) => n.id === sourceNodeId
  );

  if (!sourceNode) {
    return null;
  }

  const nodeId = generateId('scene');
  const data: SceneNodeData = {
    title: 'Generating...',
    sceneType: sceneType,
    content: '',
    summary: 'Synthesizing scene...',
    visualPrompt: '',
    status: 'loading',
  };

  const node: WeaverNode = {
    id: nodeId,
    type: 'scene',
    position: {
      x: sourceNode.position.x + 400,
      y: sourceNode.position.y,
    },
    data,
  };

  const edge = {
    id: `edge-${sourceNodeId}-${nodeId}`,
    source: sourceNodeId,
    target: nodeId,
    animated: true,
    style: { stroke: 'hsl(var(--primary))' },
  };

  return { node, edge };
};

/**
 * Extracts character context from a character node for scene generation
 */
const extractCharacterContext = (
  nodeData: CharacterNodeData
): CharacterGenerationResponse => {
  return {
    name: nodeData.name,
    tagline: nodeData.tagline ?? '',
    bio: nodeData.bio ?? '',
    visual_prompt: nodeData.visualPrompt ?? '',
    traits: nodeData.traits,
  };
};

export const handleSceneMutationSuccess = (
  updateNode: UpdateNodeFn,
  data: SceneGenerationResponse,
  variables: SceneGenerationInput,
  context: SceneMutationContext | undefined
): void => {
  if (!context?.nodeId) return;
  updateNode(context.nodeId, (node) => {
    const updatedData: SceneNodeData = {
      ...(node.data as SceneNodeData),
      title: data.title,
      content: data.content,
      summary: data.summary,
      visualPrompt: data.visual_prompt,
      sceneType: variables.sceneType,
      status: 'idle',
    };
    return { ...node, data: updatedData };
  });
};

export const handleSceneMutationError = (
  updateNode: UpdateNodeFn,
  error: unknown,
  context: SceneMutationContext | undefined
): void => {
  if (!context?.nodeId) return;
  const message = error instanceof Error ? error.message : 'Scene generation failed';
  updateNode(context.nodeId, (node) => {
    const updatedData: SceneNodeData = {
      ...(node.data as SceneNodeData),
      status: 'error',
      errorMessage: message,
    };
    return { ...node, data: updatedData };
  });
};

export function useSceneGeneration() {
  const addNode = useWeaverAddNode();
  const updateNode = useWeaverUpdateNode();

  return useMutation({
    mutationFn: async (input: SceneGenerationInput): Promise<SceneGenerationResponse> => {
      // Get source node to extract character context
      const sourceNode = useWeaverStore.getState().nodes.find(
        (n) => n.id === input.sourceNodeId
      );

      if (!sourceNode) {
        throw new Error('Source character node not found');
      }

      const characterContext = extractCharacterContext(
        sourceNode.data as CharacterNodeData
      );

      const request: SceneGenerationRequest = {
        character_context: characterContext,
        scene_type: input.sceneType,
        tone: input.tone,
      };

      return generateScene(request);
    },
    onMutate: async (input) => {
      const result = createOptimisticSceneNode(input.sourceNodeId, input.sceneType);

      if (!result) {
        // Source node not found - mutation will fail in mutationFn
        return { nodeId: '' } satisfies SceneMutationContext;
      }

      const { node, edge } = result;
      addNode(node);

      // Add edge directly to store
      useWeaverStore.setState((state) => ({
        edges: [...state.edges, edge],
      }));

      return { nodeId: node.id } satisfies SceneMutationContext;
    },
    onSuccess: (data, variables, context) => {
      handleSceneMutationSuccess(updateNode, data, variables, context);
    },
    onError: (error, _variables, context) => {
      handleSceneMutationError(updateNode, error, context);
    },
  });
}
