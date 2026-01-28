import { useMutation } from '@tanstack/react-query';
import { generateCharacter } from '@/lib/api';
import { generateId } from '@/lib/utils';
import type {
  CharacterGenerationRequest,
  CharacterGenerationResponse,
} from '@/types/schemas';
import type { CharacterNodeData } from '../components/nodes/CharacterNode';
import {
  useWeaverAddNode,
  useWeaverStore,
  useWeaverUpdateNode,
  type WeaverNode,
} from '../store/weaverStore';

export type MutationContext = {
  nodeId: string;
};

export type UpdateNodeFn = (
  nodeId: string,
  updater: (node: WeaverNode) => WeaverNode
) => void;

export const createOptimisticNode = (
  input: CharacterGenerationRequest
): WeaverNode => {
  const existingNodes = useWeaverStore.getState().nodes;
  const index = existingNodes.length;
  const baseX = 160 + (index % 3) * 240;
  const baseY = 120 + Math.floor(index / 3) * 180;
  const data: CharacterNodeData = {
    name: 'Generating...',
    role: input.archetype || 'New Character',
    traits: [],
    status: 'loading',
    tagline: 'Synthesizing character profile',
  };

  return {
    id: generateId('char'),
    type: 'character',
    position: {
      x: baseX + Math.random() * 40,
      y: baseY + Math.random() * 40,
    },
    data,
  };
};

export const handleMutationSuccess = (
  updateNode: UpdateNodeFn,
  data: CharacterGenerationResponse,
  variables: CharacterGenerationRequest,
  context: MutationContext | undefined
): void => {
  if (!context?.nodeId) return;
  updateNode(context.nodeId, (node) => {
    const updatedData: CharacterNodeData = {
      ...(node.data as CharacterNodeData),
      name: data.name,
      role: variables.archetype,
      traits: data.traits,
      status: 'idle',
      tagline: data.tagline,
      bio: data.bio,
      visualPrompt: data.visual_prompt,
    };
    return { ...node, data: updatedData };
  });
};

export const handleMutationError = (
  updateNode: UpdateNodeFn,
  error: unknown,
  context: MutationContext | undefined
): void => {
  if (!context?.nodeId) return;
  const message = error instanceof Error ? error.message : 'Generation failed';
  updateNode(context.nodeId, (node) => {
    const updatedData: CharacterNodeData = {
      ...(node.data as CharacterNodeData),
      status: 'error',
      errorMessage: message,
    };
    return { ...node, data: updatedData };
  });
};

export function useCharacterGeneration() {
  const addNode = useWeaverAddNode();
  const updateNode = useWeaverUpdateNode();

  return useMutation({
    mutationFn: generateCharacter,
    onMutate: async (input) => {
      const node = createOptimisticNode(input);
      addNode(node);
      return { nodeId: node.id } satisfies MutationContext;
    },
    onSuccess: (data, variables, context) => {
      handleMutationSuccess(updateNode, data, variables, context);
    },
    onError: (error, _variables, context) => {
      handleMutationError(updateNode, error, context);
    },
  });
}
