/**
 * WebSocket Testing Utilities
 * Provides utilities for testing WebSocket functionality in isolation
 */

import { vi } from 'vitest';
import { MockWebSocket } from './setup';

interface WebSocketTestUtilities {
  mockWebSocket: typeof MockWebSocket;
  createMockWebSocketInstance: (url: string) => MockWebSocket;
  simulateWebSocketConnection: (ws: MockWebSocket) => void;
  simulateWebSocketMessage: (ws: MockWebSocket, data: any) => void;
  simulateWebSocketError: (ws: MockWebSocket) => void;
  simulateWebSocketClose: (ws: MockWebSocket, code?: number, reason?: string) => void;
}

/**
 * Create a mock WebSocket instance for testing
 */
export function createMockWebSocketInstance(url: string): MockWebSocket {
  return new MockWebSocket(url);
}

/**
 * Simulate a successful WebSocket connection
 */
export function simulateWebSocketConnection(ws: MockWebSocket): void {
  ws.readyState = MockWebSocket.OPEN;
  if (ws.onopen) {
    ws.onopen(new Event('open'));
  }
}

/**
 * Simulate receiving a WebSocket message
 */
export function simulateWebSocketMessage(ws: MockWebSocket, data: any): void {
  ws.simulateMessage(data);
}

/**
 * Simulate a WebSocket error
 */
export function simulateWebSocketError(ws: MockWebSocket): void {
  ws.simulateError();
}

/**
 * Simulate WebSocket connection close
 */
export function simulateWebSocketClose(
  ws: MockWebSocket, 
  code: number = 1000, 
  reason: string = ''
): void {
  ws.close(code, reason);
}

/**
 * Create a complete mock of useWebSocketProgress hook for testing
 */
export function createMockWebSocketHook(overrides: any = {}) {
  return vi.fn(() => ({
    isConnected: false,
    lastUpdate: null,
    error: null,
    connectionAttempts: 0,
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendMessage: vi.fn(),
    ...overrides,
  }));
}

/**
 * Mock WebSocket progress update data for testing
 */
export function createMockProgressUpdate(overrides: any = {}) {
  return {
    generation_id: 'test-123',
    progress: 50,
    stage: 'generating',
    stage_detail: 'Processing character interactions...',
    estimated_time_remaining: 60,
    active_agents: ['CharacterAgent', 'StoryAgent'],
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * WebSocket testing utilities object
 */
export const websocketTestUtils: WebSocketTestUtilities = {
  mockWebSocket: MockWebSocket,
  createMockWebSocketInstance,
  simulateWebSocketConnection,
  simulateWebSocketMessage,
  simulateWebSocketError,
  simulateWebSocketClose,
};

export { MockWebSocket };