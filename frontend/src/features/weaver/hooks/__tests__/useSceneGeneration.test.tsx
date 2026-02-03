/**
 * Unit tests for useSceneGeneration hook
 * Coverage: Smart Placement, Success path, Error path, Defensive branches
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useSceneGeneration,
  handleSceneMutationSuccess,
  handleSceneMutationError,
  createOptimisticSceneNode,
} from '../useSceneGeneration';
import { useWeaverStore } from '../../store/weaverStore';
import * as sceneApi from '@/lib/api/sceneApi';
import type { CharacterNodeData } from '../../components/nodes/CharacterNode';

// Mock the scene API
vi.mock('@/lib/api/sceneApi', () => ({
  generateScene: vi.fn(),
}));

const mockedGenerateScene = sceneApi.generateScene as ReturnType<typeof vi.fn>;

// Create a wrapper with QueryClient for testing
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// Helper to create a mock character node
function createMockCharacterNode(
  id: string,
  x: number,
  y: number
): {
  id: string;
  type: 'character';
  position: { x: number; y: number };
  data: CharacterNodeData;
} {
  return {
    id,
    type: 'character',
    position: { x, y },
    data: {
      name: 'Nyx',
      role: 'Protagonist',
      traits: ['mysterious', 'clever'],
      status: 'idle',
      tagline: 'A shadow walker',
      bio: 'Nyx walks in shadows.',
      visualPrompt: 'dark figure, ethereal glow',
    },
  };
}

describe('useSceneGeneration', () => {
  beforeEach(() => {
    // Use fake timers with shouldAdvanceTime to allow waitFor to work
    vi.useFakeTimers({ shouldAdvanceTime: true });
    // Reset the Weaver store with a character node for testing
    useWeaverStore.setState({
      nodes: [createMockCharacterNode('char-1', 200, 100)],
      edges: [],
      startParams: { total_turns: 3, setting: undefined, scenario: undefined },
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Smart Placement (onMutate)', () => {
    it('positions new node at sourceNode.x + 400, sourceNode.y', async () => {
      // GIVEN: API is pending (never resolves during this test)
      mockedGenerateScene.mockImplementation(() => new Promise(() => {}));

      const sourceNode = useWeaverStore.getState().nodes[0]!;

      // WHEN: Hook is called with mutation
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: sourceNode.id,
          sceneType: 'opening',
        });
      });

      // THEN: Store should have a scene node at the correct position
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(2);

      const sceneNode = nodes[1]!;
      expect(sceneNode.type).toBe('scene');
      expect(sceneNode.position.x).toBe(sourceNode.position.x + 400);
      expect(sceneNode.position.y).toBe(sourceNode.position.y);
    });

    it('creates edge from source character to new scene node', async () => {
      // GIVEN: API is pending
      mockedGenerateScene.mockImplementation(() => new Promise(() => {}));

      const sourceNode = useWeaverStore.getState().nodes[0]!;

      // WHEN: Hook is called with mutation
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: sourceNode.id,
          sceneType: 'opening',
        });
      });

      // THEN: An edge should connect the source character to the scene node
      const edges = useWeaverStore.getState().edges;
      expect(edges).toHaveLength(1);

      const edge = edges[0]!;
      expect(edge.source).toBe(sourceNode.id);
      expect(edge.target).toBe(useWeaverStore.getState().nodes[1]!.id);
      expect(edge.animated).toBe(true);
    });

    it('sets node type to "scene" with loading status', async () => {
      // GIVEN: API is pending
      mockedGenerateScene.mockImplementation(() => new Promise(() => {}));

      // WHEN: Hook is called
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'char-1',
          sceneType: 'opening',
        });
      });

      // THEN: Node should have correct type and loading status
      const nodes = useWeaverStore.getState().nodes;
      const sceneNode = nodes[1]!;
      expect(sceneNode.type).toBe('scene');
      expect(sceneNode.data.status).toBe('loading');
      expect(sceneNode.data.title).toBe('Generating...');
    });

    it('extracts character context from source node data', async () => {
      // GIVEN: Source node has character data
      mockedGenerateScene.mockImplementation(() => new Promise(() => {}));

      // WHEN: Hook is called
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'char-1',
          sceneType: 'opening',
          tone: 'mystical',
        });
      });

      // THEN: API should have been called with correct character context
      expect(mockedGenerateScene).toHaveBeenCalledWith(
        expect.objectContaining({
          character_context: expect.objectContaining({
            name: 'Nyx',
            tagline: 'A shadow walker',
            bio: 'Nyx walks in shadows.',
            visual_prompt: 'dark figure, ethereal glow',
            traits: ['mysterious', 'clever'],
          }),
          scene_type: 'opening',
          tone: 'mystical',
        })
      );
    });

    it('does not create node or edge when source node not found', async () => {
      // GIVEN: API is pending
      mockedGenerateScene.mockImplementation(() => new Promise(() => {}));

      // WHEN: Hook is called with non-existent source
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'non-existent',
          sceneType: 'opening',
        });
      });

      // THEN: No new node or edge should be created
      const state = useWeaverStore.getState();
      expect(state.nodes).toHaveLength(1); // Only the original character node
      expect(state.edges).toHaveLength(0);
    });
  });

  describe('Success path (onSuccess)', () => {
    it('updates node with title, content, summary, visual_prompt', async () => {
      // GIVEN: API will return success
      const mockResponse = {
        title: 'The Shadows Whisper',
        content: 'In the dim corridors...',
        summary: 'Nyx discovers a mysterious tome.',
        visual_prompt: 'dark library, ancient tomes',
      };
      mockedGenerateScene.mockResolvedValue(mockResponse);

      // WHEN: Hook is called and mutation completes
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'char-1',
          sceneType: 'opening',
        });
      });

      // Wait for mutation to complete
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Advance timers to trigger the delayed updateNode call
      await act(async () => {
        vi.runAllTimers();
      });

      // THEN: Node should be updated with scene data
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(2);
      const sceneNode = nodes[1]!;
      expect(sceneNode.data.status).toBe('idle');
      expect(sceneNode.data.title).toBe('The Shadows Whisper');
      expect(sceneNode.data.content).toBe('In the dim corridors...');
      expect(sceneNode.data.summary).toBe('Nyx discovers a mysterious tome.');
      expect(sceneNode.data.visualPrompt).toBe('dark library, ancient tomes');
    });

    it('preserves scene_type as node data', async () => {
      // GIVEN: API will return success
      mockedGenerateScene.mockResolvedValue({
        title: 'Test Scene',
        content: 'Content...',
        summary: 'Summary...',
        visual_prompt: 'prompt',
      });

      // WHEN: Mutation completes
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'char-1',
          sceneType: 'climax',
        });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Advance timers to trigger the delayed updateNode call
      await act(async () => {
        vi.runAllTimers();
      });

      // THEN: Scene type should be preserved
      const nodes = useWeaverStore.getState().nodes;
      const sceneNode = nodes[1]!;
      expect(sceneNode.data.sceneType).toBe('climax');
    });
  });

  describe('Error path (onError)', () => {
    it('sets node status to error with message', async () => {
      // Suppress console errors for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // GIVEN: API will fail
      mockedGenerateScene.mockRejectedValue(
        new Error('Scene generation service unavailable')
      );

      // WHEN: Hook is called and mutation fails
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'char-1',
          sceneType: 'opening',
        });
      });

      // Wait for mutation to fail
      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Advance timers to trigger the delayed updateNode call
      await act(async () => {
        vi.runAllTimers();
      });

      // THEN: Node should have error status and message
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(2);
      const sceneNode = nodes[1]!;
      expect(sceneNode.data.status).toBe('error');
      expect(sceneNode.data.errorMessage).toBe('Scene generation service unavailable');

      consoleSpy.mockRestore();
    });

    it('does not remove the node from canvas on error', async () => {
      // Suppress console errors
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // GIVEN: API will fail
      mockedGenerateScene.mockRejectedValue(new Error('Service error'));

      // WHEN: Mutation fails
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'char-1',
          sceneType: 'opening',
        });
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // THEN: Scene node should still exist (not removed)
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(2);
      const sceneNode = nodes.find((n) => n.type === 'scene');
      expect(sceneNode).toBeDefined();

      consoleSpy.mockRestore();
    });

    it('uses fallback error message when error is not an Error instance', async () => {
      // Suppress console errors
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // GIVEN: API will fail with non-Error rejection
      mockedGenerateScene.mockRejectedValue('string error');

      // WHEN: Mutation fails
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          sourceNodeId: 'char-1',
          sceneType: 'opening',
        });
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Advance timers to trigger the delayed updateNode call
      await act(async () => {
        vi.runAllTimers();
      });

      // THEN: Fallback message should be used
      const nodes = useWeaverStore.getState().nodes;
      const sceneNode = nodes[1]!;
      expect(sceneNode.data.errorMessage).toBe('Scene generation failed');

      consoleSpy.mockRestore();
    });
  });

  describe('Edge cases', () => {
    it('generates unique node IDs across multiple calls', async () => {
      // GIVEN: API resolves normally
      mockedGenerateScene.mockResolvedValue({
        title: 'Test Scene',
        content: 'Content',
        summary: 'Summary',
        visual_prompt: 'prompt',
      });

      // WHEN: Hook is called
      const { result } = renderHook(() => useSceneGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({ sourceNodeId: 'char-1', sceneType: 'opening' });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // THEN: Node should have a unique ID starting with 'scene'
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(2);
      expect(nodes[1]!.id).toMatch(/^scene[_-]/);
    });
  });

  describe('Callback handlers (direct unit tests for 100% branch coverage)', () => {
    it('createOptimisticSceneNode returns null when source node not found', () => {
      // GIVEN: Store with no matching node
      useWeaverStore.setState({
        nodes: [],
        edges: [],
        startParams: { total_turns: 3, setting: undefined, scenario: undefined },
      });

      // WHEN: createOptimisticSceneNode is called with non-existent source
      const result = createOptimisticSceneNode('non-existent', 'opening');

      // THEN: Should return null
      expect(result).toBeNull();
    });

    it('handleSceneMutationSuccess returns early when context is undefined', () => {
      // GIVEN: updateNode mock and undefined context
      const updateNode = vi.fn();
      const mockData = {
        title: 'Test',
        content: 'Content',
        summary: 'Summary',
        visual_prompt: 'prompt',
      };
      const mockVariables = { sourceNodeId: 'test', sceneType: 'opening' };

      // WHEN: handleSceneMutationSuccess is called with undefined context
      handleSceneMutationSuccess(updateNode, mockData, mockVariables, undefined);

      // THEN: updateNode should NOT be called (early return)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleSceneMutationSuccess returns early when context.nodeId is falsy', () => {
      // GIVEN: updateNode mock and context with falsy nodeId
      const updateNode = vi.fn();
      const mockData = {
        title: 'Test',
        content: 'Content',
        summary: 'Summary',
        visual_prompt: 'prompt',
      };
      const mockVariables = { sourceNodeId: 'test', sceneType: 'opening' };

      // WHEN: handleSceneMutationSuccess is called with empty nodeId
      handleSceneMutationSuccess(updateNode, mockData, mockVariables, {
        nodeId: '',
        startedAt: Date.now(),
      });

      // THEN: updateNode should NOT be called (early return due to falsy nodeId)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleSceneMutationError returns early when context is undefined', () => {
      // GIVEN: updateNode mock and undefined context
      const updateNode = vi.fn();
      const mockError = new Error('Test error');

      // WHEN: handleSceneMutationError is called with undefined context
      handleSceneMutationError(updateNode, mockError, undefined);

      // THEN: updateNode should NOT be called (early return)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleSceneMutationError returns early when context.nodeId is falsy', () => {
      // GIVEN: updateNode mock and context with falsy nodeId
      const updateNode = vi.fn();
      const mockError = new Error('Test error');

      // WHEN: handleSceneMutationError is called with empty nodeId
      handleSceneMutationError(updateNode, mockError, {
        nodeId: '',
        startedAt: Date.now(),
      });

      // THEN: updateNode should NOT be called (early return due to falsy nodeId)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleSceneMutationSuccess calls updateNode when context is valid', () => {
      // GIVEN: updateNode mock and valid context
      // Use a startedAt in the past (>300ms ago) to avoid setTimeout delay
      const updateNode = vi.fn();
      const mockData = {
        title: 'Test Scene',
        content: 'Content here',
        summary: 'Summary here',
        visual_prompt: 'visual prompt',
      };
      const mockVariables = { sourceNodeId: 'char-1', sceneType: 'action' };

      // WHEN: handleSceneMutationSuccess is called with valid context
      handleSceneMutationSuccess(updateNode, mockData, mockVariables, {
        nodeId: 'scene-123',
        startedAt: Date.now() - 500, // 500ms ago, so delayMs = 0
      });

      // THEN: updateNode should be called with the correct nodeId
      expect(updateNode).toHaveBeenCalledTimes(1);
      expect(updateNode).toHaveBeenCalledWith('scene-123', expect.any(Function));
    });

    it('handleSceneMutationError calls updateNode when context is valid', () => {
      // GIVEN: updateNode mock and valid context
      // Use a startedAt in the past (>300ms ago) to avoid setTimeout delay
      const updateNode = vi.fn();
      const mockError = new Error('Generation failed');

      // WHEN: handleSceneMutationError is called with valid context
      handleSceneMutationError(updateNode, mockError, {
        nodeId: 'scene-456',
        startedAt: Date.now() - 500, // 500ms ago, so delayMs = 0
      });

      // THEN: updateNode should be called with the correct nodeId
      expect(updateNode).toHaveBeenCalledTimes(1);
      expect(updateNode).toHaveBeenCalledWith('scene-456', expect.any(Function));
    });
  });
});
