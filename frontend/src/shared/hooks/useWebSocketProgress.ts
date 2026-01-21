/**
 * useWebSocketProgress - WebSocket connection for generation progress
 * Features: connection quality monitoring, auto-reconnect
 */
import { useEffect, useRef, useCallback, useState } from 'react';

interface ProgressUpdate {
  taskId: string;
  progress: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message?: string;
  metadata?: Record<string, unknown>;
}

interface UseWebSocketProgressOptions {
  url: string;
  taskId?: string;
  onProgress?: (update: ProgressUpdate) => void;
  onComplete?: (taskId: string) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  maxRetries?: number;
}

interface ConnectionQuality {
  latency: number;
  status: 'excellent' | 'good' | 'poor' | 'disconnected';
}

interface UseWebSocketProgressReturn {
  isConnected: boolean;
  connectionQuality: ConnectionQuality;
  currentProgress: ProgressUpdate | null;
  reconnect: () => void;
  disconnect: () => void;
}

export function useWebSocketProgress({
  url,
  taskId,
  onProgress,
  onComplete,
  onError,
  enabled = true,
  maxRetries = 5,
}: UseWebSocketProgressOptions): UseWebSocketProgressReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [currentProgress, setCurrentProgress] = useState<ProgressUpdate | null>(null);
  const [connectionQuality, setConnectionQuality] = useState<ConnectionQuality>({
    latency: 0,
    status: 'disconnected',
  });

  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const lastPingRef = useRef<number>(0);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<number | null>(null);
  const manualCloseRef = useRef(false);

  const disconnect = useCallback(() => {
    manualCloseRef.current = true;
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionQuality({ latency: 0, status: 'disconnected' });
  }, []);

  const measureLatency = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      lastPingRef.current = Date.now();
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled || wsRef.current) return;

    try {
      manualCloseRef.current = false;
      const wsUrl = taskId ? `${url}?taskId=${taskId}` : url;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        retryCountRef.current = 0;
        setConnectionQuality({ latency: 0, status: 'excellent' });

        // Start ping interval for latency monitoring
        pingIntervalRef.current = window.setInterval(measureLatency, 5000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle pong for latency measurement
          if (data.type === 'pong') {
            const latency = Date.now() - lastPingRef.current;
            setConnectionQuality({
              latency,
              status: latency < 100 ? 'excellent' : latency < 300 ? 'good' : 'poor',
            });
            return;
          }

          // Handle progress updates
          if (data.type === 'progress' || data.progress !== undefined) {
            const update: ProgressUpdate = {
              taskId: data.taskId || taskId || '',
              progress: data.progress || 0,
              status: data.status || 'running',
              message: data.message,
              metadata: data.metadata,
            };

            setCurrentProgress(update);
            onProgress?.(update);

            if (update.status === 'completed') {
              onComplete?.(update.taskId);
            }
          }
        } catch {
          // Non-JSON message
        }
      };

      ws.onerror = (event) => {
        onError?.(new Error('WebSocket error: ' + (event as ErrorEvent).message));
      };

      ws.onclose = () => {
        setIsConnected(false);
        setConnectionQuality({ latency: 0, status: 'disconnected' });
        wsRef.current = null;

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        if (!enabled || manualCloseRef.current) {
          return;
        }

        if (retryCountRef.current < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current += 1;
          retryTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (error) {
      onError?.(error as Error);
    }
  }, [
    url,
    taskId,
    enabled,
    maxRetries,
    onProgress,
    onComplete,
    onError,
    measureLatency,
  ]);

  const reconnect = useCallback(() => {
    disconnect();
    retryCountRef.current = 0;
    connect();
  }, [disconnect, connect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    connectionQuality,
    currentProgress,
    reconnect,
    disconnect,
  };
}
