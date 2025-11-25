import { useState, useEffect, useRef, useCallback } from 'react';
import { logger } from '../services/logging/LoggerFactory';

export interface ProgressUpdate {
  generation_id: string;
  progress: number;
  stage: string;
  stage_detail: string;
  estimated_time_remaining: number;
  active_agents: string[];
  timestamp: string;
}

interface UseWebSocketProgressOptions {
  generationId: string | null;
  enabled?: boolean;
  onUpdate?: (update: ProgressUpdate) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface WebSocketProgressState {
  isConnected: boolean;
  lastUpdate: ProgressUpdate | null;
  error: string | null;
  connectionAttempts: number;
  connectionQuality: 'excellent' | 'good' | 'poor' | 'unknown';
  lastHeartbeat: number | null;
  messageLatency: number | null;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_BASE = 1000; // 1 second base delay
const CONNECTION_TIMEOUT = 10000; // 10 second connection timeout
const HEARTBEAT_INTERVAL = 30000; // 30 second heartbeat

export function useWebSocketProgress({
  generationId,
  enabled = true,
  onUpdate,
  onError,
  onConnect,
  onDisconnect,
}: UseWebSocketProgressOptions) {
  const [state, setState] = useState<WebSocketProgressState>({
    isConnected: false,
    lastUpdate: null,
    error: null,
    connectionAttempts: 0,
    connectionQuality: 'unknown',
    lastHeartbeat: null,
    messageLatency: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isUnmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (!generationId || !enabled || isUnmountedRef.current) {
      return;
    }

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/stories/progress/${generationId}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // Set connection timeout
      const connectionTimer = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.close();
          setState(prev => ({
            ...prev,
            error: 'Connection timeout. Please check your network.',
            connectionQuality: 'poor',
          }));
        }
      }, CONNECTION_TIMEOUT);

      ws.onopen = () => {
        if (isUnmountedRef.current) return;
        
        clearTimeout(connectionTimer);
        
        setState(prev => ({
          ...prev,
          isConnected: true,
          error: null,
          connectionAttempts: 0,
          connectionQuality: 'excellent',
          lastHeartbeat: Date.now(),
        }));
        onConnect?.();
        
        // Start heartbeat monitoring
        startHeartbeatMonitoring();
      };

      ws.onmessage = (event) => {
        if (isUnmountedRef.current) return;
        
        const messageReceiveTime = Date.now();
        
        try {
          const data = JSON.parse(event.data);
          
          // Handle heartbeat responses
          if (data.type === 'heartbeat') {
            const latency = messageReceiveTime - (state.lastHeartbeat || messageReceiveTime);
            setState(prev => ({
              ...prev,
              lastHeartbeat: messageReceiveTime,
              messageLatency: latency,
              connectionQuality: latency < 200 ? 'excellent' : latency < 500 ? 'good' : 'poor',
            }));
            return;
          }
          
          // Handle progress updates
          const update: ProgressUpdate = data;
          
          setState(prev => ({
            ...prev,
            lastUpdate: update,
            error: null,
            lastHeartbeat: messageReceiveTime,
          }));
          
          onUpdate?.(update);
        } catch (error) {
          logger.error('Failed to parse WebSocket message:', error);
          const parseError = new Error('Failed to parse progress update');
          setState(prev => ({
            ...prev,
            error: parseError.message,
          }));
          onError?.(parseError);
        }
      };

      ws.onerror = (error) => {
        if (isUnmountedRef.current) return;
        
        logger.error('WebSocket error:', error);
        const wsError = new Error('WebSocket connection error');
        setState(prev => ({
          ...prev,
          error: wsError.message,
          isConnected: false,
        }));
        onError?.(wsError);
      };

      ws.onclose = (event) => {
        if (isUnmountedRef.current) return;
        
        setState(prev => ({
          ...prev,
          isConnected: false,
        }));
        onDisconnect?.();

        // Attempt to reconnect if not a clean close and within retry limits
        if (!event.wasClean && state.connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            RECONNECT_DELAY_BASE * Math.pow(1.5, state.connectionAttempts),
            10000 // Max 10 second delay
          );
          
          setState(prev => ({
            ...prev,
            connectionAttempts: prev.connectionAttempts + 1,
          }));

          logger.info(`WebSocket reconnecting in ${delay}ms (attempt ${state.connectionAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            if (!isUnmountedRef.current) {
              connect();
            }
          }, delay);
        } else if (!event.wasClean) {
          // Max attempts reached
          setState(prev => ({
            ...prev,
            error: 'Connection failed after multiple attempts. Please refresh to retry.',
          }));
        }
      };

    } catch (error) {
      logger.error('Failed to create WebSocket connection:', error);
      const connectionError = new Error('Failed to establish WebSocket connection');
      setState(prev => ({
        ...prev,
        error: connectionError.message,
        isConnected: false,
      }));
      onError?.(connectionError);
    }
    // Intentionally excluding `state.lastHeartbeat` and `connect` from deps:
    // - state.lastHeartbeat: Used only for latency calculation inside onmessage handler,
    //   and reading the stale value is acceptable since we update it immediately after
    // - connect: Would cause infinite reconnection loop since connect is called within
    //   the onclose handler for reconnection logic
    // - startHeartbeatMonitoring: Called inside onopen but doesn't need to trigger reconnect
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generationId, enabled, onUpdate, onError, onConnect, onDisconnect, state.connectionAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounting');
      wsRef.current = null;
    }

    setState({
      isConnected: false,
      lastUpdate: null,
      error: null,
      connectionAttempts: 0,
      connectionQuality: 'unknown',
      lastHeartbeat: null,
      messageLatency: null,
    });
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);
  
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setState(prev => ({ ...prev, lastHeartbeat: Date.now() }));
      wsRef.current.send('ping');
    }
  }, []);
  
  const startHeartbeatMonitoring = useCallback(() => {
    const heartbeatTimer = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        sendHeartbeat();
      }
    }, HEARTBEAT_INTERVAL);
    
    return () => clearInterval(heartbeatTimer);
  }, [sendHeartbeat]);

  // Effect to manage connection lifecycle
  useEffect(() => {
    if (generationId && enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [generationId, enabled, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isUnmountedRef.current = true;
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected: state.isConnected,
    lastUpdate: state.lastUpdate,
    error: state.error,
    connectionAttempts: state.connectionAttempts,
    connectionQuality: state.connectionQuality,
    messageLatency: state.messageLatency,
    connect,
    disconnect,
    sendMessage,
    sendHeartbeat,
  };
}