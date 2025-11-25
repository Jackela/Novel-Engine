/**
 * WebSocket Hook for Real-time Novel Engine Communication
 * =====================================================
 *
 * Advanced React hook for managing WebSocket connections with:
 * - Automatic reconnection with exponential backoff
 * - Message queuing and deduplication
 * - Connection state management
 * - Error handling and recovery
 * - Performance optimization
 */

/* eslint-disable react-refresh/only-export-components */
import React, { useEffect, useRef, useCallback, useState } from 'react';
import { usePerformanceOptimizer } from './usePerformanceOptimizer';
import { logger } from '../services/logging/LoggerFactory';

// Types
export interface WebSocketMessage {
  id: string;
  type: string;
  data: unknown;
  timestamp: number;
  priority: 'low' | 'normal' | 'high' | 'critical';
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  lastError: Error | null;
  reconnectAttempts: number;
  messageQueue: WebSocketMessage[];
  latency: number;
}

export interface WebSocketOptions {
  url: string;
  protocols?: string[];
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
  maxReconnectInterval?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
  enableCompression?: boolean;
  enableMessageDeduplication?: boolean;
}

export interface WebSocketHookResult {
  state: WebSocketState;
  sendMessage: (message: Omit<WebSocketMessage, 'id' | 'timestamp'>) => void;
  connect: () => void;
  disconnect: () => void;
  clearQueue: () => void;
  getConnectionHealth: () => ConnectionHealth;
}

interface ConnectionHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency: number;
  uptime: number;
  messagesSent: number;
  messagesReceived: number;
  errorsCount: number;
}

// WebSocket hook implementation
export const useWebSocket = (options: WebSocketOptions): WebSocketHookResult => {
  const {
    url,
    protocols = [],
    maxReconnectAttempts = 10,
    reconnectInterval = 1000,
    maxReconnectInterval = 30000,
    heartbeatInterval = 30000,
    messageQueueSize = 1000,
    enableCompression = true,
    enableMessageDeduplication = true
  } = options;

  // Performance optimization hook
  const { optimizeForRealTime } = usePerformanceOptimizer();

  // WebSocket refs and state
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const messageHistoryRef = useRef<Set<string>>(new Set());
  const connectionStartTime = useRef<number>(Date.now());
  const statsRef = useRef({
    messagesSent: 0,
    messagesReceived: 0,
    errorsCount: 0,
    lastPingTime: 0,
    lastPongTime: 0
  });

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    lastError: null,
    reconnectAttempts: 0,
    messageQueue: [],
    latency: 0
  });

  // Message deduplication
  const isDuplicateMessage = useCallback((messageId: string): boolean => {
    if (!enableMessageDeduplication) return false;
    
    if (messageHistoryRef.current.has(messageId)) {
      return true;
    }
    
    // Add to history and cleanup if too large (optimized for mobile memory)
    messageHistoryRef.current.add(messageId);
    if (messageHistoryRef.current.size > 1000) {
      const oldestMessages = Array.from(messageHistoryRef.current).slice(0, 500);
      oldestMessages.forEach(id => messageHistoryRef.current.delete(id));
    }
    
    return false;
  }, [enableMessageDeduplication]);

  // Calculate reconnect delay with exponential backoff
  const getReconnectDelay = useCallback((attempt: number): number => {
    const delay = Math.min(
      reconnectInterval * Math.pow(2, attempt),
      maxReconnectInterval
    );
    // Add jitter to prevent thundering herd
    return delay + Math.random() * 1000;
  }, [reconnectInterval, maxReconnectInterval]);

  // Send heartbeat ping
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const pingTime = Date.now();
      statsRef.current.lastPingTime = pingTime;
      
      wsRef.current.send(JSON.stringify({
        id: `heartbeat_${pingTime}`,
        type: 'ping',
        data: { timestamp: pingTime },
        priority: 'normal',
        timestamp: pingTime
      }));
    }
  }, []);

  // Process message queue
  const processMessageQueue = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    setState(prevState => {
      const queue = [...prevState.messageQueue];
      
      // Sort by priority and timestamp
      queue.sort((a, b) => {
        const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
        const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
        return priorityDiff !== 0 ? priorityDiff : a.timestamp - b.timestamp;
      });

      // Send messages
      for (const message of queue) {
        try {
          const messageString = enableCompression 
            ? JSON.stringify(message) // In real implementation, use compression library
            : JSON.stringify(message);
          
          wsRef.current!.send(messageString);
          statsRef.current.messagesSent++;
        } catch (error) {
          logger.error('Failed to send queued message:', error);
          statsRef.current.errorsCount++;
        }
      }

      return {
        ...prevState,
        messageQueue: []
      };
    });
  }, [enableCompression]);

  // Handle WebSocket message
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Check for duplicate
      if (isDuplicateMessage(message.id)) {
        return;
      }

      // Handle heartbeat response
      if (message.type === 'pong') {
        statsRef.current.lastPongTime = Date.now();
        const latency = statsRef.current.lastPongTime - statsRef.current.lastPingTime;
        setState(prevState => ({
          ...prevState,
          latency
        }));
        return;
      }

      statsRef.current.messagesReceived++;

      // Dispatch message to application
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: message
      }));

    } catch (error) {
      logger.error('Failed to parse WebSocket message:', error);
      statsRef.current.errorsCount++;
    }
  }, [isDuplicateMessage]);

  // Handle WebSocket open
  const handleOpen = useCallback(() => {
    logger.info('WebSocket connected');
    connectionStartTime.current = Date.now();
    
    setState(prevState => ({
      ...prevState,
      isConnected: true,
      isConnecting: false,
      lastError: null,
      reconnectAttempts: 0
    }));

    // Process any queued messages
    processMessageQueue();

    // Start heartbeat
    if (heartbeatInterval > 0) {
      heartbeatIntervalRef.current = setInterval(sendHeartbeat, heartbeatInterval);
    }

    // Optimize performance for real-time
    optimizeForRealTime();

  }, [processMessageQueue, sendHeartbeat, heartbeatInterval, optimizeForRealTime]);

  // Handle WebSocket close
  const handleClose = useCallback((event: CloseEvent) => {
    logger.info('WebSocket closed:', event.code, event.reason);
    
    setState(prevState => ({
      ...prevState,
      isConnected: false,
      isConnecting: false
    }));

    // Clear heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    // Attempt reconnection if not a clean close
    if (event.code !== 1000 && state.reconnectAttempts < maxReconnectAttempts) {
      const delay = getReconnectDelay(state.reconnectAttempts);
      
      logger.info(`Reconnecting in ${delay}ms (attempt ${state.reconnectAttempts + 1}/${maxReconnectAttempts})`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        setState(prevState => ({
          ...prevState,
          reconnectAttempts: prevState.reconnectAttempts + 1,
          isConnecting: true
        }));
        connect();
      }, delay);
    }
    // Intentionally excluding `connect` from deps:
    // - Including it would cause a circular dependency: handleClose -> connect -> handleClose
    // - The connect function is called explicitly within the timeout callback
    // - This pattern is required for the exponential backoff reconnection logic
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.reconnectAttempts, maxReconnectAttempts, getReconnectDelay]);

  // Handle WebSocket error
  const handleError = useCallback((event: Event) => {
    logger.error('WebSocket error:', event);
    statsRef.current.errorsCount++;
    
    setState(prevState => ({
      ...prevState,
      lastError: new Error('WebSocket connection error'),
      isConnecting: false
    }));
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      setState(prevState => ({
        ...prevState,
        isConnecting: true,
        lastError: null
      }));

      const ws = new WebSocket(url, protocols);
      
      ws.onopen = handleOpen;
      ws.onclose = handleClose;
      ws.onerror = handleError;
      ws.onmessage = handleMessage;

      wsRef.current = ws;

    } catch (error) {
      logger.error('Failed to create WebSocket connection:', error);
      setState(prevState => ({
        ...prevState,
        lastError: error as Error,
        isConnecting: false
      }));
    }
  }, [url, protocols, handleOpen, handleClose, handleError, handleMessage]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setState(prevState => ({
      ...prevState,
      isConnected: false,
      isConnecting: false,
      reconnectAttempts: 0
    }));
  }, []);

  // Send message
  const sendMessage = useCallback((message: Omit<WebSocketMessage, 'id' | 'timestamp'>) => {
    const fullMessage: WebSocketMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      ...message
    };

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        const messageString = enableCompression 
          ? JSON.stringify(fullMessage) // Use compression in real implementation
          : JSON.stringify(fullMessage);
        
        wsRef.current.send(messageString);
        statsRef.current.messagesSent++;
      } catch (error) {
        logger.error('Failed to send message:', error);
        statsRef.current.errorsCount++;
        
        // Queue message for retry
        setState(prevState => ({
          ...prevState,
          messageQueue: [...prevState.messageQueue, fullMessage].slice(-messageQueueSize)
        }));
      }
    } else {
      // Queue message if not connected
      setState(prevState => ({
        ...prevState,
        messageQueue: [...prevState.messageQueue, fullMessage].slice(-messageQueueSize)
      }));
    }
  }, [enableCompression, messageQueueSize]);

  // Clear message queue
  const clearQueue = useCallback(() => {
    setState(prevState => ({
      ...prevState,
      messageQueue: []
    }));
  }, []);

  // Get connection health
  const getConnectionHealth = useCallback((): ConnectionHealth => {
    const now = Date.now();
    const uptime = now - connectionStartTime.current;
    
    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    
    if (!state.isConnected) {
      status = 'unhealthy';
    } else if (state.latency > 1000 || statsRef.current.errorsCount > 10) {
      status = 'degraded';
    }

    return {
      status,
      latency: state.latency,
      uptime,
      messagesSent: statsRef.current.messagesSent,
      messagesReceived: statsRef.current.messagesReceived,
      errorsCount: statsRef.current.errorsCount
    };
  }, [state.isConnected, state.latency]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  return {
    state,
    sendMessage,
    connect,
    disconnect,
    clearQueue,
    getConnectionHealth
  };
};

// WebSocket context for sharing connection across components
export const WebSocketContext = React.createContext<WebSocketHookResult | null>(null);

export const WebSocketProvider: React.FC<{
  children: React.ReactNode;
  options: WebSocketOptions;
}> = ({ children, options }) => {
  const webSocket = useWebSocket(options);
  
  return (
    <WebSocketContext.Provider value={webSocket}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = (): WebSocketHookResult => {
  const context = React.useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider');
  }
  return context;
};
