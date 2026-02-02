/**
 * useCharacterGeneration - Hook for AI-powered character generation with optimistic UI
 *
 * This hook implements the Optimistic UI pattern for character generation:
 * 1. onMutate: Immediately creates a "loading" placeholder node on the canvas
 * 2. mutationFn: Calls the backend API to generate character data
 * 3. onSuccess: Updates the placeholder node with the generated character data
 * 4. onError: Updates the placeholder node to show error state
 *
 * This pattern provides instant visual feedback to users while the LLM generates
 * content in the background (which can take several seconds).
 *
 * @module useCharacterGeneration
 */
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

/** Context passed through the mutation lifecycle to track the optimistic node */
export type MutationContext = {
  nodeId: string;
  startedAt: number;
};

/** Function signature for updating a node in the Weaver store */
export type UpdateNodeFn = (
  nodeId: string,
  updater: (node: WeaverNode) => WeaverNode
) => void;

/**
 * Creates an optimistic placeholder node while character generation is in progress.
 *
 * The node is positioned using a grid layout algorithm:
 * - Calculates position based on existing node count
 * - Arranges in 3-column grid with slight random offset for visual interest
 *
 * @param input - The character generation request parameters
 * @returns A WeaverNode with loading state to display immediately
 */
export const createOptimisticNode = (input: CharacterGenerationRequest): WeaverNode => {
  const existingNodes = useWeaverStore.getState().nodes;
  const index = existingNodes.length;
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
      x: 160 + (index % 3) * 320,
      y: 120 + Math.floor(index / 3) * 240,
    },
    data,
  };
};

/**
 * Handles successful character generation by updating the optimistic node.
 *
 * Transforms the loading placeholder into a fully populated character node
 * with all generated attributes (name, traits, bio, visual prompt).
 *
 * @param updateNode - Function to update a node in the store
 * @param data - The generated character data from the API
 * @param variables - The original request parameters (used for archetype)
 * @param context - Contains the nodeId of the optimistic node to update
 */
export const handleMutationSuccess = (
  updateNode: UpdateNodeFn,
  data: CharacterGenerationResponse,
  variables: CharacterGenerationRequest,
  context: MutationContext | undefined
): void => {
  if (!context?.nodeId) return;
  const MIN_LOADING_MS = 300;
  const delayMs = Math.max(0, MIN_LOADING_MS - (Date.now() - context.startedAt));
  const applyUpdate = () => {
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
  if (delayMs > 0) {
    window.setTimeout(applyUpdate, delayMs);
  } else {
    applyUpdate();
  }
};

/**
 * Handles character generation errors by updating the optimistic node to error state.
 *
 * Instead of removing the node, we keep it visible with an error indicator
 * so users can see that generation was attempted and failed. The error message
 * is displayed to help with debugging.
 *
 * @param updateNode - Function to update a node in the store
 * @param error - The error that occurred during generation
 * @param context - Contains the nodeId of the optimistic node to update
 */
export const handleMutationError = (
  updateNode: UpdateNodeFn,
  error: unknown,
  context: MutationContext | undefined
): void => {
  if (!context?.nodeId) return;
  const message = error instanceof Error ? error.message : 'Generation failed';
  const MIN_LOADING_MS = 300;
  const delayMs = Math.max(0, MIN_LOADING_MS - (Date.now() - context.startedAt));
  const applyUpdate = () => {
    updateNode(context.nodeId, (node) => {
      const updatedData: CharacterNodeData = {
        ...(node.data as CharacterNodeData),
        status: 'error',
        errorMessage: message,
      };
      return { ...node, data: updatedData };
    });
  };
  if (delayMs > 0) {
    window.setTimeout(applyUpdate, delayMs);
  } else {
    applyUpdate();
  }
};

/**
 * Hook for generating AI characters with optimistic UI updates.
 *
 * Implements the optimistic update pattern:
 * 1. Shows a loading placeholder immediately when generation starts
 * 2. Updates with real data when generation completes
 * 3. Shows error state if generation fails
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useCharacterGeneration();
 *
 * const handleGenerate = () => {
 *   mutate({
 *     concept: 'A wise old wizard',
 *     archetype: 'Mentor',
 *     tone: 'mysterious'
 *   });
 * };
 * ```
 *
 * @returns A TanStack Query mutation object with generate function and status
 */
export function useCharacterGeneration() {
  const addNode = useWeaverAddNode();
  const updateNode = useWeaverUpdateNode();

  return useMutation({
    mutationFn: generateCharacter,
    onMutate: async (input) => {
      const node = createOptimisticNode(input);
      addNode(node);
      return { nodeId: node.id, startedAt: Date.now() } satisfies MutationContext;
    },
    onSuccess: (data, variables, context) => {
      handleMutationSuccess(updateNode, data, variables, context);
    },
    onError: (error, _variables, context) => {
      handleMutationError(updateNode, error, context);
    },
  });
}
