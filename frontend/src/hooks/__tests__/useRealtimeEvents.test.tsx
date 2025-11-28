import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { useRealtimeEvents } from '../useRealtimeEvents';
import React, { useState, useEffect } from 'react';

/**
 * Mock EventSource implementation for testing.
 *
 * These tests use a TestComponent that renders the hook's output to DOM elements,
 * combined with waitFor for async state changes.
 */
describe('useRealtimeEvents', () => {
  // Global mocks for controlling the EventSource from tests
  let mockOnOpen: (() => void) | null = null;
  let mockOnMessage: ((data: Record<string, unknown>) => void) | null = null;
  let mockOnError: (() => void) | null = null;
  let mockClose: (() => void) | null = null;
  let mockUrl: string | null = null;
  let mockReadyState = 0;
  let instanceCreated = false;

  class MockEventSourceImpl {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSED = 2;
    CONNECTING = 0;
    OPEN = 1;
    CLOSED = 2;

    constructor(url: string) {
      mockUrl = url;
      mockReadyState = this.CONNECTING;
      instanceCreated = true;
    }

    get url() {
      return mockUrl || '';
    }

    get readyState() {
      return mockReadyState;
    }

    set onopen(fn: ((event: Event) => void) | null) {
      mockOnOpen = () => {
        if (mockReadyState === 0 && fn) {
          mockReadyState = 1;
          fn(new Event('open'));
        }
      };
    }

    set onmessage(fn: ((event: MessageEvent) => void) | null) {
      mockOnMessage = (data: Record<string, unknown>) => {
        if (mockReadyState === 1 && fn) {
          fn(new MessageEvent('message', { data: JSON.stringify(data) }));
        }
      };
    }

    set onerror(fn: ((event: Event) => void) | null) {
      mockOnError = () => {
        if (fn) {
          mockReadyState = 2;
          fn(new Event('error'));
        }
      };
    }

    get onopen() {
      return null;
    }

    get onmessage() {
      return null;
    }

    get onerror() {
      return null;
    }

    close() {
      mockReadyState = 2;
      if (mockClose) mockClose();
    }
  }

  beforeEach(() => {
    mockOnOpen = null;
    mockOnMessage = null;
    mockOnError = null;
    mockClose = null;
    mockUrl = null;
    mockReadyState = 0;
    instanceCreated = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (global as any).EventSource = MockEventSourceImpl;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // Test component that renders hook state and provides a trigger mechanism
  interface TestComponentProps {
    options?: Parameters<typeof useRealtimeEvents>[0];
    onHookReady?: (helpers: {
      triggerOpen: () => void;
      triggerMessage: (data: Record<string, unknown>) => void;
      triggerError: () => void;
    }) => void;
  }

  const TestComponent: React.FC<TestComponentProps> = ({ options, onHookReady }) => {
    const hookResult = useRealtimeEvents(options);
    const [, setTick] = useState(0);

    // Expose trigger functions to parent via callback
    useEffect(() => {
      if (onHookReady) {
        onHookReady({
          triggerOpen: () => {
            mockOnOpen?.();
            // Force a tick to allow React to process
            setTick(t => t + 1);
          },
          triggerMessage: (data: Record<string, unknown>) => {
            mockOnMessage?.(data);
            setTick(t => t + 1);
          },
          triggerError: () => {
            mockOnError?.();
            setTick(t => t + 1);
          },
        });
      }
    }, [onHookReady]);

    return (
      <div>
        <div data-testid="connection-state">{hookResult.connectionState}</div>
        <div data-testid="loading">{String(hookResult.loading)}</div>
        <div data-testid="error">{hookResult.error?.message ?? 'null'}</div>
        <div data-testid="events-count">{hookResult.events.length}</div>
        <div data-testid="first-event-id">{hookResult.events[0]?.id ?? 'none'}</div>
        <div data-testid="last-event-id">{hookResult.events[hookResult.events.length - 1]?.id ?? 'none'}</div>
      </div>
    );
  };

  it('establishes SSE connection and sets connectionState to connected', async () => {
    let helpers: { triggerOpen: () => void } | null = null;

    render(
      <TestComponent
        onHookReady={(h) => {
          helpers = h;
        }}
      />
    );

    expect(screen.getByTestId('connection-state')).toHaveTextContent('connecting');
    expect(screen.getByTestId('loading')).toHaveTextContent('true');

    // Wait for hook to be ready (EventSource handlers attached)
    await waitFor(() => {
      expect(mockOnOpen).not.toBeNull();
    });

    // Trigger open
    await act(async () => {
      helpers?.triggerOpen();
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
    });

    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('error')).toHaveTextContent('null');
  });

  it('receives and parses events correctly', async () => {
    let helpers: { triggerOpen: () => void; triggerMessage: (data: Record<string, unknown>) => void } | null = null;

    render(
      <TestComponent
        onHookReady={(h) => {
          helpers = h;
        }}
      />
    );

    await waitFor(() => {
      expect(mockOnOpen).not.toBeNull();
    });

    await act(async () => {
      helpers?.triggerOpen();
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
    });

    const testEvent = {
      id: 'evt-1',
      type: 'character',
      title: 'Test Event',
      description: 'Test description',
      timestamp: Date.now(),
      severity: 'medium',
      characterName: 'Test Character',
    };

    await act(async () => {
      helpers?.triggerMessage(testEvent);
    });

    await waitFor(() => {
      expect(screen.getByTestId('events-count')).toHaveTextContent('1');
    });

    expect(screen.getByTestId('first-event-id')).toHaveTextContent('evt-1');
  });

  it('shows error state when connection fails', async () => {
    let helpers: { triggerError: () => void } | null = null;

    render(
      <TestComponent
        options={{ maxRetries: 0 }}
        onHookReady={(h) => {
          helpers = h;
        }}
      />
    );

    await waitFor(() => {
      expect(mockOnError).not.toBeNull();
    });

    await act(async () => {
      helpers?.triggerError();
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-state')).toHaveTextContent('error');
    });

    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('error')).toHaveTextContent('Failed to connect after 0 attempts');
  });

  it('respects maxEvents buffer limit', async () => {
    const maxEvents = 5;
    let helpers: { triggerOpen: () => void; triggerMessage: (data: Record<string, unknown>) => void } | null = null;

    render(
      <TestComponent
        options={{ maxEvents }}
        onHookReady={(h) => {
          helpers = h;
        }}
      />
    );

    await waitFor(() => {
      expect(mockOnOpen).not.toBeNull();
    });

    await act(async () => {
      helpers?.triggerOpen();
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
    });

    // Send more events than the buffer limit
    await act(async () => {
      for (let i = 1; i <= 10; i++) {
        helpers?.triggerMessage({
          id: `evt-${i}`,
          type: 'system',
          title: `Event ${i}`,
          description: `Description ${i}`,
          timestamp: Date.now() + i,
          severity: 'low',
        });
      }
    });

    await waitFor(() => {
      expect(screen.getByTestId('events-count')).toHaveTextContent('5');
    });

    // Verify newest events are kept (evt-10 should be first, evt-6 should be last)
    expect(screen.getByTestId('first-event-id')).toHaveTextContent('evt-10');
    expect(screen.getByTestId('last-event-id')).toHaveTextContent('evt-6');
  });

  it('cleans up EventSource on unmount', async () => {
    let helpers: { triggerOpen: () => void } | null = null;
    // Variable tracks close() call but we verify via mockReadyState instead
    mockClose = () => {
      // Close callback executed - verified by mockReadyState check below
    };

    const { unmount } = render(
      <TestComponent
        onHookReady={(h) => {
          helpers = h;
        }}
      />
    );

    await waitFor(() => {
      expect(mockOnOpen).not.toBeNull();
    });

    await act(async () => {
      helpers?.triggerOpen();
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
    });

    unmount();

    expect(mockReadyState).toBe(2); // CLOSED
  });

  it('handles invalid JSON in event data gracefully', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    let onMessageFn: ((event: MessageEvent) => void) | null = null;
    let helpers: { triggerOpen: () => void } | null = null;

    // Override the mock to capture the raw onmessage handler
    class CapturingMockEventSource {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSED = 2;
      CONNECTING = 0;
      OPEN = 1;
      CLOSED = 2;
      url: string;

      constructor(url: string) {
        this.url = url;
        mockReadyState = 0;
        instanceCreated = true;
      }

      get readyState() {
        return mockReadyState;
      }

      set onopen(fn: ((event: Event) => void) | null) {
        mockOnOpen = () => {
          if (mockReadyState === 0 && fn) {
            mockReadyState = 1;
            fn(new Event('open'));
          }
        };
      }

      set onmessage(fn: ((event: MessageEvent) => void) | null) {
        onMessageFn = fn;
      }

      set onerror(fn: ((event: Event) => void) | null) {
        mockOnError = () => {
          if (fn) {
            mockReadyState = 2;
            fn(new Event('error'));
          }
        };
      }

      get onopen() {
        return null;
      }

      get onmessage() {
        return onMessageFn;
      }

      get onerror() {
        return null;
      }

      close() {
        mockReadyState = 2;
      }
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (global as any).EventSource = CapturingMockEventSource;

    render(
      <TestComponent
        onHookReady={(h) => {
          helpers = h;
        }}
      />
    );

    await waitFor(() => {
      expect(mockOnOpen).not.toBeNull();
    });

    await act(async () => {
      helpers?.triggerOpen();
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
    });

    // Simulate receiving invalid JSON
    await act(async () => {
      if (onMessageFn && mockReadyState === 1) {
        onMessageFn(new MessageEvent('message', { data: 'not valid json' }));
      }
    });

    expect(screen.getByTestId('events-count')).toHaveTextContent('0');
    expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
    // The logger prefixes with [ERROR], so we check that it was called with something containing our message
    expect(consoleSpy).toHaveBeenCalled();
    const errorCall = consoleSpy.mock.calls.find(call =>
      typeof call[0] === 'string' && call[0].includes('Failed to parse SSE event data')
    );
    expect(errorCall).toBeDefined();
    // The second argument should contain the SyntaxError
    expect(errorCall?.[1]).toBeDefined();
    expect(errorCall?.[1].name).toBe('SyntaxError');

    consoleSpy.mockRestore();
  });

  it('skips events with missing required fields', async () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    let helpers: { triggerOpen: () => void; triggerMessage: (data: Record<string, unknown>) => void } | null = null;

    render(
      <TestComponent
        onHookReady={(h) => {
          helpers = h;
        }}
      />
    );

    await waitFor(() => {
      expect(mockOnOpen).not.toBeNull();
    });

    await act(async () => {
      helpers?.triggerOpen();
    });

    await waitFor(() => {
      expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');
    });

    // Send event missing required fields
    await act(async () => {
      helpers?.triggerMessage({
        description: 'Test description',
        timestamp: Date.now(),
        severity: 'low',
        // Missing: id, type, title
      });
    });

    expect(screen.getByTestId('events-count')).toHaveTextContent('0');
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Received malformed SSE event'),
      expect.objectContaining({ data: expect.any(String) })
    );

    consoleWarnSpy.mockRestore();
  });

  it('uses custom endpoint when provided', async () => {
    const customEndpoint = '/custom/events/stream';
    render(<TestComponent options={{ endpoint: customEndpoint }} />);

    await waitFor(() => {
      expect(mockUrl).toBe(customEndpoint);
    });
  });

  it('respects enabled flag', () => {
    render(<TestComponent options={{ enabled: false }} />);

    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('connection-state')).toHaveTextContent('disconnected');
    expect(instanceCreated).toBe(false);
  });
});
