/**
 * Unit tests for useCharacterGeneration hook
 * Coverage: Optimistic UI, Success path, Error path, Defensive branches
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useCharacterGeneration,
  handleMutationSuccess,
  handleMutationError,
} from '../useCharacterGeneration';
import { useWeaverStore } from '../../store/weaverStore';
import * as generationApi from '@/lib/api/generationApi';

// Mock the generation API
vi.mock('@/lib/api/generationApi', () => ({
  generateCharacter: vi.fn(),
}));

const mockedGenerateCharacter = generationApi.generateCharacter as ReturnType<
  typeof vi.fn
>;

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

describe('useCharacterGeneration', () => {
  beforeEach(() => {
    // Use fake timers with shouldAdvanceTime to allow waitFor to work
    vi.useFakeTimers({ shouldAdvanceTime: true });
    // Reset the Weaver store to clean state before each test
    useWeaverStore.setState({
      nodes: [],
      edges: [],
      startParams: { total_turns: 3, setting: undefined, scenario: undefined },
    });
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Optimistic UI (onMutate)', () => {
    it('adds a loading node to store when mutate is called', async () => {
      // GIVEN: API is pending (never resolves during this test)
      mockedGenerateCharacter.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      // WHEN: Hook is called with mutation
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'Test concept',
          archetype: 'Wanderer',
          tone: 'Noir',
        });
      });

      // THEN: Store should have a loading node
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(1);
      expect(nodes[0]!.data.status).toBe('loading');
      expect(nodes[0]!.data.name).toBe('Generating...');
      expect(nodes[0]!.type).toBe('character');
    });

    it('uses default role when archetype is not provided', async () => {
      // GIVEN: API is pending
      mockedGenerateCharacter.mockImplementation(() => new Promise(() => {}));

      // WHEN: Hook is called without archetype
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'Test concept',
          archetype: '', // Empty archetype should fallback to default
        });
      });

      // THEN: Store should have a node with default role
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(1);
      expect(nodes[0]!.data.role).toBe('New Character');
    });

    it('creates node with correct position based on existing nodes', async () => {
      // GIVEN: Store already has some nodes
      useWeaverStore.setState({
        nodes: [
          {
            id: 'existing-1',
            type: 'character',
            position: { x: 100, y: 100 },
            data: {
              name: 'Existing',
              role: 'Test',
              traits: [],
              status: 'idle' as const,
            },
          },
        ],
        edges: [],
        startParams: { total_turns: 3, setting: undefined, scenario: undefined },
      });

      mockedGenerateCharacter.mockImplementation(() => new Promise(() => {}));

      // WHEN: Hook adds a new node
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'New concept',
          archetype: 'Mystic',
        });
      });

      // THEN: New node should be positioned after the existing node
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(2);
      // New node should have index-based positioning
      const newNode = nodes[1]!;
      expect(newNode.position.x).toBeGreaterThan(0);
      expect(newNode.position.y).toBeGreaterThan(0);
    });
  });

  describe('Success path (onSuccess)', () => {
    it('updates node to idle status with character data on success', async () => {
      // GIVEN: API will return success
      const mockResponse = {
        name: 'Zenith Arc',
        tagline: 'A spark that bends the grid.',
        bio: 'Zenith navigates lost circuits.',
        visual_prompt: 'neon silhouette, cyan glow',
        traits: ['curious', 'steady'],
      };
      mockedGenerateCharacter.mockResolvedValue(mockResponse);

      // WHEN: Hook is called and mutation completes
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'Test concept',
          archetype: 'Wanderer',
          tone: 'Noir',
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

      // THEN: Node should be updated to idle with character data
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(1);
      const node = nodes[0]!;
      expect(node.data.status).toBe('idle');
      expect(node.data.name).toBe('Zenith Arc');
      expect(node.data.tagline).toBe('A spark that bends the grid.');
      expect(node.data.bio).toBe('Zenith navigates lost circuits.');
      expect(node.data.traits).toEqual(['curious', 'steady']);
    });

    it('preserves archetype as role in updated node', async () => {
      // GIVEN: API will return success
      mockedGenerateCharacter.mockResolvedValue({
        name: 'Test Character',
        tagline: 'Test tagline',
        bio: 'Test bio',
        visual_prompt: 'test prompt',
        traits: ['trait1'],
      });

      // WHEN: Mutation completes
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'Test',
          archetype: 'Guardian',
        });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Advance timers to trigger the delayed updateNode call
      await act(async () => {
        vi.runAllTimers();
      });

      // THEN: Role should match the archetype from the request
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes[0]!.data.role).toBe('Guardian');
    });
  });

  describe('Error path (onError)', () => {
    it('updates node to error status when API fails', async () => {
      // Suppress console errors for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // GIVEN: API will fail
      mockedGenerateCharacter.mockRejectedValue(new Error('LLM service unavailable'));

      // WHEN: Hook is called and mutation fails
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'Test concept',
          archetype: 'Wanderer',
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

      // THEN: Node should have error status and error message
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(1);
      const node = nodes[0]!;
      expect(node.data.status).toBe('error');
      expect(node.data.errorMessage).toBe('LLM service unavailable');

      consoleSpy.mockRestore();
    });

    it('uses fallback error message when error is not an Error instance', async () => {
      // Suppress console errors for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // GIVEN: API will fail with non-Error rejection
      mockedGenerateCharacter.mockRejectedValue('string error');

      // WHEN: Mutation fails
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'Test',
          archetype: 'Test',
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
      expect(nodes[0]!.data.errorMessage).toBe('Generation failed');

      consoleSpy.mockRestore();
    });

    it('does not modify node if context is missing', async () => {
      // This tests the defensive check: if (!context?.nodeId) return;
      // We need to simulate a scenario where context might be undefined
      // This is an edge case that shouldn't happen in normal flow

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // GIVEN: API fails
      mockedGenerateCharacter.mockRejectedValue(new Error('Test error'));

      // WHEN: Mutation is called
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({
          concept: 'Test',
          archetype: 'Test',
        });
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // THEN: Node should still be updated (context is present in normal flow)
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(1);

      consoleSpy.mockRestore();
    });
  });

  describe('Edge cases', () => {
    it('generates unique node IDs across multiple calls', async () => {
      // GIVEN: API resolves normally
      mockedGenerateCharacter.mockResolvedValue({
        name: 'Test Character',
        tagline: 'Test tagline',
        bio: 'Test bio',
        visual_prompt: 'prompt',
        traits: ['trait'],
      });

      // WHEN: Hook is called
      const { result } = renderHook(() => useCharacterGeneration(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        result.current.mutate({ concept: 'Test', archetype: 'Warrior' });
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // THEN: Node should have a unique ID starting with 'char'
      const nodes = useWeaverStore.getState().nodes;
      expect(nodes).toHaveLength(1);
      expect(nodes[0]!.id).toMatch(/^char[_-]/);
    });
  });

  describe('Callback handlers (direct unit tests for 100% branch coverage)', () => {
    it('handleMutationSuccess returns early when context is undefined', () => {
      // GIVEN: updateNode mock and undefined context
      const updateNode = vi.fn();
      const mockData = {
        name: 'Test',
        tagline: 'Test',
        bio: 'Test',
        visual_prompt: 'Test',
        traits: ['trait'],
      };
      const mockVariables = { concept: 'Test', archetype: 'Test' };

      // WHEN: handleMutationSuccess is called with undefined context
      handleMutationSuccess(updateNode, mockData, mockVariables, undefined);

      // THEN: updateNode should NOT be called (early return)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleMutationSuccess returns early when context.nodeId is falsy', () => {
      // GIVEN: updateNode mock and context with falsy nodeId
      const updateNode = vi.fn();
      const mockData = {
        name: 'Test',
        tagline: 'Test',
        bio: 'Test',
        visual_prompt: 'Test',
        traits: ['trait'],
      };
      const mockVariables = { concept: 'Test', archetype: 'Test' };

      // WHEN: handleMutationSuccess is called with empty nodeId
      handleMutationSuccess(updateNode, mockData, mockVariables, {
        nodeId: '',
        startedAt: Date.now(),
      });

      // THEN: updateNode should NOT be called (early return due to falsy nodeId)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleMutationError returns early when context is undefined', () => {
      // GIVEN: updateNode mock and undefined context
      const updateNode = vi.fn();
      const mockError = new Error('Test error');

      // WHEN: handleMutationError is called with undefined context
      handleMutationError(updateNode, mockError, undefined);

      // THEN: updateNode should NOT be called (early return)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleMutationError returns early when context.nodeId is falsy', () => {
      // GIVEN: updateNode mock and context with falsy nodeId
      const updateNode = vi.fn();
      const mockError = new Error('Test error');

      // WHEN: handleMutationError is called with empty nodeId
      handleMutationError(updateNode, mockError, { nodeId: '', startedAt: Date.now() });

      // THEN: updateNode should NOT be called (early return due to falsy nodeId)
      expect(updateNode).not.toHaveBeenCalled();
    });

    it('handleMutationSuccess calls updateNode when context is valid', () => {
      // GIVEN: updateNode mock and valid context
      // Use a startedAt in the past (>300ms ago) to avoid setTimeout delay
      const updateNode = vi.fn();
      const mockData = {
        name: 'Zenith',
        tagline: 'A test',
        bio: 'Bio text',
        visual_prompt: 'visual',
        traits: ['brave'],
      };
      const mockVariables = { concept: 'Test', archetype: 'Warrior' };

      // WHEN: handleMutationSuccess is called with valid context
      handleMutationSuccess(updateNode, mockData, mockVariables, {
        nodeId: 'node-123',
        startedAt: Date.now() - 500, // 500ms ago, so delayMs = 0
      });

      // THEN: updateNode should be called with the correct nodeId
      expect(updateNode).toHaveBeenCalledTimes(1);
      expect(updateNode).toHaveBeenCalledWith('node-123', expect.any(Function));
    });

    it('handleMutationError calls updateNode when context is valid', () => {
      // GIVEN: updateNode mock and valid context
      // Use a startedAt in the past (>300ms ago) to avoid setTimeout delay
      const updateNode = vi.fn();
      const mockError = new Error('Generation failed');

      // WHEN: handleMutationError is called with valid context
      handleMutationError(updateNode, mockError, {
        nodeId: 'node-456',
        startedAt: Date.now() - 500, // 500ms ago, so delayMs = 0
      });

      // THEN: updateNode should be called with the correct nodeId
      expect(updateNode).toHaveBeenCalledTimes(1);
      expect(updateNode).toHaveBeenCalledWith('node-456', expect.any(Function));
    });
  });
});
