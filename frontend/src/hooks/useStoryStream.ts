/**
 * useStoryStream - Hook for handling SSE streaming from narrative generation.
 *
 * Why: Provides a centralized hook for connecting to the backend SSE endpoint,
 * managing the EventSource lifecycle, buffering incoming tokens, and handling
 * completion/error events. This hook encapsulates the complexity of streaming
 * text generation for the editor UI.
 */
import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * A chunk of streamed narrative content.
 */
interface StreamChunk {
  /** Event type: chunk, done, or error */
  type: 'chunk' | 'done' | 'error';
  /** Text content of this chunk */
  content: string;
  /** Sequence number for ordering */
  sequence: number;
  /** Optional metadata (present in done event) */
  metadata?: StreamMetadata;
}

/**
 * Metadata included in the done event.
 */
interface StreamMetadata {
  /** Total chunks received */
  total_chunks: number;
  /** Total characters generated */
  total_characters: number;
  /** Generation time in milliseconds */
  generation_time_ms: number;
  /** Whether mock mode was used */
  mock_mode: boolean;
}

/**
 * Request body for starting a stream.
 */
export interface StreamRequest {
  /** Optional UUID of the scene to generate content for */
  scene_id?: string;
  /** Optional custom prompt for generation */
  prompt?: string;
  /** Optional context string to inform generation */
  context?: string;
  /** Maximum tokens to generate (50-4000, default 500) */
  max_tokens?: number;
}

/**
 * State returned by the hook.
 */
interface StreamState {
  /** Accumulated text buffer from all chunks */
  buffer: string;
  /** Whether streaming is currently in progress */
  isStreaming: boolean;
  /** Error message if streaming failed */
  error: string | null;
  /** Metadata from the completed stream */
  metadata: StreamMetadata | null;
  /** Whether the stream completed successfully */
  isComplete: boolean;
}

/**
 * Callbacks for stream events.
 */
export interface StreamCallbacks {
  /** Called when a new chunk arrives with the chunk content */
  onChunk?: (content: string, sequence: number) => void;
  /** Called when the stream completes successfully */
  onComplete?: (metadata: StreamMetadata) => void;
  /** Called when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Actions returned by the hook.
 */
interface StreamActions {
  /** Start streaming with the given request */
  startStream: (request?: StreamRequest) => void;
  /** Stop the current stream */
  stopStream: () => void;
  /** Clear the buffer and reset state */
  reset: () => void;
}

const API_BASE_URL = '/api';

/**
 * Parse SSE data line into StreamChunk.
 *
 * Why: SSE events come as "data: {...}" lines, we need to extract
 * and parse the JSON payload.
 */
function parseSSEData(data: string): StreamChunk | null {
  try {
    return JSON.parse(data) as StreamChunk;
  } catch {
    console.error('Failed to parse SSE data:', data);
    return null;
  }
}

/**
 * Hook for managing SSE streaming from narrative generation.
 *
 * Why: Encapsulates all the complexity of EventSource management,
 * chunk buffering, and event handling. Provides a clean interface
 * for components to start/stop streams and access accumulated text.
 *
 * @param callbacks - Optional callbacks for stream events
 * @returns State and actions for managing the stream
 */
export function useStoryStream(callbacks?: StreamCallbacks): StreamState & StreamActions {
  const [state, setState] = useState<StreamState>({
    buffer: '',
    isStreaming: false,
    error: null,
    metadata: null,
    isComplete: false,
  });

  // Use refs for callbacks to avoid stale closures in EventSource handlers
  const callbacksRef = useRef(callbacks);
  useEffect(() => {
    callbacksRef.current = callbacks;
  }, [callbacks]);

  // Track abort controller for stopping fetch requests
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Start streaming from the narrative generation endpoint.
   *
   * Why: Uses fetch with ReadableStream instead of EventSource because
   * EventSource only supports GET requests, but our endpoint uses POST.
   */
  const startStream = useCallback((request?: StreamRequest) => {
    // Stop any existing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Reset state for new stream
    setState({
      buffer: '',
      isStreaming: true,
      error: null,
      metadata: null,
      isComplete: false,
    });

    // Create abort controller for this stream
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Build request body with defaults
    const body: StreamRequest = {
      max_tokens: 500,
      ...request,
    };

    // Start streaming via fetch
    const streamUrl = `${API_BASE_URL}/narrative/generate/stream`;

    fetch(streamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal: abortController.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body reader available');
        }

        const decoder = new TextDecoder();
        let partialLine = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          // Decode chunk and process SSE lines
          const text = decoder.decode(value, { stream: true });
          const lines = (partialLine + text).split('\n');

          // Keep last partial line for next iteration
          partialLine = lines.pop() || '';

          for (const line of lines) {
            // SSE data lines start with "data: "
            if (line.startsWith('data: ')) {
              const data = line.slice(6); // Remove "data: " prefix
              const chunk = parseSSEData(data);

              if (!chunk) {
                continue;
              }

              switch (chunk.type) {
                case 'chunk':
                  // Append content to buffer (add newline since lines come separately)
                  setState((prev) => ({
                    ...prev,
                    buffer: prev.buffer + (prev.buffer ? '\n' : '') + chunk.content,
                  }));

                  // Call chunk callback
                  callbacksRef.current?.onChunk?.(chunk.content, chunk.sequence);
                  break;

                case 'done':
                  // Stream completed successfully
                  setState((prev) => ({
                    ...prev,
                    isStreaming: false,
                    isComplete: true,
                    metadata: chunk.metadata || null,
                  }));

                  // Call complete callback
                  if (chunk.metadata) {
                    callbacksRef.current?.onComplete?.(chunk.metadata);
                  }
                  break;

                case 'error':
                  // Error occurred during streaming
                  setState((prev) => ({
                    ...prev,
                    isStreaming: false,
                    error: chunk.content || 'Unknown streaming error',
                  }));

                  // Call error callback
                  callbacksRef.current?.onError?.(chunk.content || 'Unknown streaming error');
                  break;
              }
            }
          }
        }
      })
      .catch((error: unknown) => {
        // Ignore abort errors (user stopped stream)
        if (error instanceof Error && error.name === 'AbortError') {
          return;
        }

        const errorMessage = error instanceof Error ? error.message : 'Stream connection failed';

        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: errorMessage,
        }));

        callbacksRef.current?.onError?.(errorMessage);
      });
  }, []);

  /**
   * Stop the current stream.
   *
   * Why: Provides a way to cancel an in-progress generation,
   * useful for user-initiated cancellation or component unmount.
   */
  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setState((prev) => ({
      ...prev,
      isStreaming: false,
    }));
  }, []);

  /**
   * Clear the buffer and reset all state.
   *
   * Why: Allows resetting the hook state for a fresh start,
   * useful when switching scenes or starting new generation.
   */
  const reset = useCallback(() => {
    stopStream();
    setState({
      buffer: '',
      isStreaming: false,
      error: null,
      metadata: null,
      isComplete: false,
    });
  }, [stopStream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    ...state,
    startStream,
    stopStream,
    reset,
  };
}

export default useStoryStream;
