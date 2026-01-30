/**
 * useSceneGeneration - Hook for AI-powered scene generation with optimistic UI
 *
 * This hook generates scenes based on a selected character node and implements
 * the Optimistic UI pattern with visual graph connections:
 *
 * 1. onMutate: Creates a loading scene node positioned to the right of the source
 *    character, and draws an animated edge connecting them
 * 2. mutationFn: Extracts character context and calls the scene generation API
 * 3. onSuccess: Updates the placeholder with generated scene content
 * 4. onError: Shows error state while preserving the visual connection
 *
 * The scene node is automatically linked to its source character via an animated
 * edge, creating a visual narrative flow on the canvas.
 *
 * @module useSceneGeneration
 */
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

/** Context passed through the mutation lifecycle to track the optimistic scene node */
export type SceneMutationContext = {
  nodeId: string;
};

/** Function signature for updating a node in the Weaver store */
export type UpdateNodeFn = (
  nodeId: string,
  updater: (node: WeaverNode) => WeaverNode
) => void;

/** Input parameters for scene generation */
export type SceneGenerationInput = {
  /** ID of the character node to generate a scene for */
  sourceNodeId: string;
  /** Type of scene (e.g., 'introduction', 'conflict', 'resolution') */
  sceneType: string;
  /** Optional tone modifier for the generated scene */
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

/**
 * Handles successful scene generation by updating the optimistic node.
 *
 * Transforms the loading placeholder into a fully populated scene node
 * with title, content, summary, and visual prompt for potential image generation.
 *
 * @param updateNode - Function to update a node in the store
 * @param data - The generated scene data from the API
 * @param variables - The original request parameters (used for sceneType)
 * @param context - Contains the nodeId of the optimistic node to update
 */
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

/**
 * Handles scene generation errors by updating the optimistic node to error state.
 *
 * Preserves the visual connection to the source character while indicating
 * the error state, allowing users to retry or remove the failed node.
 *
 * @param updateNode - Function to update a node in the store
 * @param error - The error that occurred during generation
 * @param context - Contains the nodeId of the optimistic node to update
 */
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

/**
 * Hook for generating AI scenes with optimistic UI updates and visual graph connections.
 *
 * Creates a scene based on a selected character node, automatically positioning
 * the new scene to the right of the source character and drawing an animated
 * connection edge between them.
 *
 * Implements the optimistic update pattern:
 * 1. Shows a loading placeholder immediately with animated edge
 * 2. Extracts character context (name, traits, bio) for scene generation
 * 3. Updates with generated scene content when complete
 * 4. Shows error state if generation fails
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useSceneGeneration();
 *
 * const handleGenerateScene = (characterNodeId: string) => {
 *   mutate({
 *     sourceNodeId: characterNodeId,
 *     sceneType: 'introduction',
 *     tone: 'dramatic'
 *   });
 * };
 * ```
 *
 * @returns A TanStack Query mutation object with generate function and status
 */
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
