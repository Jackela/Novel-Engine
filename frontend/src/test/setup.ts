import '@testing-library/jest-dom';
import { vi, beforeEach, afterEach, afterAll } from 'vitest';
import { runCleanups as runUtilCleanups } from './utils/cleanup';

// Ensure globals expected by browser-only libraries (e.g., web-vitals) exist
if (typeof globalThis.self === 'undefined') {
  (globalThis as any).self = globalThis;
}

// Global test setup for Novel Engine frontend tests

// Track cleanup functions for proper test isolation
const cleanupFunctions: (() => void)[] = [];

// Register cleanup function
export const registerCleanup = (fn: () => void) => {
  cleanupFunctions.push(fn);
};

// Run all cleanup functions
export const runCleanups = async () => {
  for (const cleanup of cleanupFunctions.splice(0)) {
    try {
      await cleanup();
    } catch (error) {
      console.warn('Cleanup function failed:', error);
    }
  }
  // Also run cleanup registry
  await runUtilCleanups();
};

// WebSocket Mock Class for Testing
class MockWebSocket {
  public static CONNECTING = 0;
  public static OPEN = 1;
  public static CLOSING = 2;
  public static CLOSED = 3;

  public readyState = MockWebSocket.CONNECTING;
  public url: string;
  public onopen: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    
    // Simulate async connection behavior
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock send operation - no actual network call
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({
        code: code || 1000,
        reason: reason || '',
        wasClean: true,
      } as CloseEvent);
    }
  }

  // Mock message simulation for testing
  simulateMessage(data: any) {
    if (this.readyState === MockWebSocket.OPEN && this.onmessage) {
      this.onmessage({
        data: JSON.stringify(data),
      } as MessageEvent);
    }
  }

  // Mock error simulation for testing
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Global WebSocket mock
Object.defineProperty(window, 'WebSocket', {
  writable: true,
  value: MockWebSocket,
});

// Mock all network requests at the global level
Object.defineProperty(window, 'fetch', {
  writable: true,
  value: vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        api: 'healthy',
        config: 'loaded',
        version: '1.0.0',
      }),
    })
  ),
});

// Mock axios for any direct usage
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({
        data: {
          api: 'healthy',
          config: 'loaded', 
          version: '1.0.0',
        },
      })),
      post: vi.fn(() => Promise.resolve({
        data: { success: true },
      })),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      getSystemStatus: vi.fn(() => Promise.resolve({
        data: {
          api: 'healthy',
          config: 'loaded',
          version: '1.0.0',
        },
      })),
    })),
    get: vi.fn(() => Promise.resolve({
      data: {
        api: 'healthy',
        config: 'loaded',
        version: '1.0.0',
      },
    })),
    post: vi.fn(() => Promise.resolve({
      data: { success: true },
    })),
  },
}));

// Mock the WebSocket hook to prevent real connections during tests
vi.mock('../hooks/useWebSocketProgress', () => ({
  useWebSocketProgress: vi.fn(() => ({
    isConnected: false,
    lastUpdate: null,
    error: null,
    connectionAttempts: 0,
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendMessage: vi.fn(),
  })),
}));

// Global test cleanup - run after each test
beforeEach(() => {
  // Clear all timers
  vi.clearAllTimers();
  vi.useRealTimers();
});

afterEach(async () => {
  // Run cleanup functions
  await runCleanups();
  // Clear all mocks
  vi.clearAllMocks();
  // Clear all timers
  vi.clearAllTimers();
  vi.useRealTimers();
});

afterAll(async () => {
  // Final cleanup after all tests
  await runCleanups();
});

// Suppress console warnings during tests
const originalConsoleWarn = console.warn;
console.warn = (...args: any[]) => {
  // Filter out specific warnings that are expected in test environment
  const message = args[0];
  if (
    typeof message === 'string' && 
    (message.includes('ReactDOMTestUtils.act') ||
     message.includes('validateDOMNesting') ||
     message.includes('WebSocket'))
  ) {
    return;
  }
  originalConsoleWarn(...args);
};

// Export mock WebSocket for tests that need to simulate messages
export { MockWebSocket };
