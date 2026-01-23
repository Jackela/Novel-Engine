import { useCallback, useEffect, useRef, useState } from 'react';

type WebSocketState = {
  isConnected: boolean;
  error?: string;
  lastMessage?: unknown;
};

const DEFAULT_STATE: WebSocketState = {
  isConnected: false,
};

const getWebSocketUrl = () =>
  (import.meta.env.VITE_WS_URL as string | undefined) || 'ws://localhost:8001/ws';

export const useWebSocketContext = () => {
  const [state, setState] = useState<WebSocketState>(DEFAULT_STATE);
  const socketRef = useRef<WebSocket | null>(null);

  const sendMessage = useCallback((payload: unknown) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    const message = typeof payload === 'string' ? payload : JSON.stringify(payload);
    socket.send(message);
  }, []);

  useEffect(() => {
    const socket = new WebSocket(getWebSocketUrl());
    socketRef.current = socket;

    socket.onopen = () => {
      setState({ isConnected: true });
    };

    socket.onerror = () => {
      setState((prev) => ({
        ...prev,
        isConnected: false,
        error: 'WebSocket error',
      }));
    };

    socket.onclose = () => {
      setState((prev) => ({
        ...prev,
        isConnected: false,
      }));
    };

    socket.onmessage = (event) => {
      let detail: unknown = event.data;
      try {
        detail = JSON.parse(event.data);
      } catch {
        // Keep raw message when not JSON
      }

      setState((prev) => ({
        ...prev,
        lastMessage: detail,
      }));

      window.dispatchEvent(new CustomEvent('websocket-message', { detail }));
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, []);

  return { state, sendMessage };
};
