/**
 * useStoryStream - Hook for SSE narrative streaming
 *
 * Connects to POST /api/narratives/stream and handles
 * real-time text generation via Server-Sent Events.
 */
import { useCallback, useRef, useState } from 'react';

export interface WorldContextEntity {
  id: string;
  name: string;
  type: string;
  description?: string;
  attributes?: Record<string, string>;
}

export interface WorldContext {
  characters: WorldContextEntity[];
  locations: WorldContextEntity[];
  entities: WorldContextEntity[];
  current_scene?: string;
  narrative_style?: string;
}

export interface StreamRequest {
  prompt: string;
  world_context: WorldContext;
  chapter_title?: string;
  tone?: string;
  max_tokens?: number;
}

export interface StreamMetadata {
  total_chunks: number;
  total_characters: number;
  generation_time_ms: number;
  model_used: string;
}

export type StreamStatus = 'idle' | 'connecting' | 'streaming' | 'complete' | 'error' | 'cancelled';

export interface UseStoryStreamReturn {
  /** Current accumulated text content */
  content: string;
  /** Current stream status */
  status: StreamStatus;
  /** Error message if status is 'error' */
  error: string | null;
  /** Metadata from completed stream */
  metadata: StreamMetadata | null;
  /** Start streaming with the given request */
  startStream: (request: StreamRequest) => void;
  /** Cancel ongoing stream */
  cancelStream: () => void;
  /** Reset state to idle */
  reset: () => void;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Custom hook for streaming narrative generation.
 *
 * Why custom hook: Encapsulates SSE connection logic, state management,
 * and error handling in a reusable way. Components just need to call
 * startStream and observe content/status.
 */
export function useStoryStream(): UseStoryStreamReturn {
  const [content, setContent] = useState('');
  const [status, setStatus] = useState<StreamStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<StreamMetadata | null>(null);

  // Use ref to track abort controller for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setContent('');
    setStatus('idle');
    setError(null);
    setMetadata(null);
    abortControllerRef.current = null;
  }, []);

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus('cancelled');
  }, []);

  const startStream = useCallback(async (request: StreamRequest) => {
    // Cancel any existing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Reset state
    setContent('');
    setError(null);
    setMetadata(null);
    setStatus('connecting');

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(`${API_BASE}/api/narratives/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      setStatus('streaming');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const event = JSON.parse(jsonStr) as {
                type: string;
                content: string;
                metadata?: StreamMetadata;
              };

              if (event.type === 'chunk') {
                setContent((prev) => prev + event.content);
              } else if (event.type === 'done') {
                if (event.metadata) {
                  setMetadata(event.metadata);
                }
                setStatus('complete');
              } else if (event.type === 'error') {
                throw new Error(event.content || 'Stream error');
              }
            } catch (parseError) {
              // Ignore malformed JSON in SSE - might be comment or keep-alive
              if (jsonStr.trim() && !jsonStr.startsWith(':')) {
                console.warn('Failed to parse SSE event:', jsonStr);
              }
            }
          }
        }
      }

      // Final status check
      if (status !== 'complete' && status !== 'error' && status !== 'cancelled') {
        setStatus('complete');
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Cancelled - status already set
        return;
      }

      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setStatus('error');
    }
  }, [status]);

  return {
    content,
    status,
    error,
    metadata,
    startStream,
    cancelStream,
    reset,
  };
}
