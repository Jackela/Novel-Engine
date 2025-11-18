import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useRealtimeEvents } from '../useRealtimeEvents';

// Mock EventSource
class MockEventSource {
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState: number = 0;
  CONNECTING = 0;
  OPEN = 1;
  CLOSED = 2;

  constructor(url: string) {
    this.url = url;
    this.readyState = this.CONNECTING;

    // Simulate connection opening after a short delay
    setTimeout(() => {
      this.readyState = this.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  close() {
    this.readyState = this.CLOSED;
  }

  // Test helper to simulate receiving a message
  simulateMessage(data: any) {
    if (this.onmessage) {
      const event = new MessageEvent('message', {
        data: JSON.stringify(data),
      });
      this.onmessage(event);
    }
  }

  // Test helper to simulate an error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

describe('useRealtimeEvents', () => {
  let eventSourceInstance: MockEventSource | null = null;

  beforeEach(() => {
    // Replace global EventSource with mock
    (global as any).EventSource = vi.fn((url: string) => {
      eventSourceInstance = new MockEventSource(url);
      return eventSourceInstance;
    });
  });

  afterEach(() => {
    eventSourceInstance = null;
    vi.restoreAllMocks();
  });

  it('establishes SSE connection and sets connectionState to connected', async () => {
    const { result } = renderHook(() => useRealtimeEvents());

    // Initially connecting
    expect(result.current.connectionState).toBe('connecting');
    expect(result.current.loading).toBe(true);

    // Wait for connection to open
    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('receives and parses events correctly', async () => {
    const { result } = renderHook(() => useRealtimeEvents());

    // Wait for connection
    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });

    // Simulate receiving an event
    const testEvent = {
      id: 'evt-1',
      type: 'character',
      title: 'Test Event',
      description: 'Test description',
      timestamp: Date.now(),
      severity: 'medium',
      characterName: 'Test Character',
    };

    eventSourceInstance?.simulateMessage(testEvent);

    await waitFor(() => {
      expect(result.current.events).toHaveLength(1);
    });

    expect(result.current.events[0]).toEqual(testEvent);
  });

  it('shows error state when connection fails', async () => {
    const { result } = renderHook(() => useRealtimeEvents());

    // Simulate connection error
    eventSourceInstance?.simulateError();

    await waitFor(() => {
      expect(result.current.connectionState).toBe('error');
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toContain('Failed to connect to event stream');
  });

  it('respects maxEvents buffer limit', async () => {
    const maxEvents = 5;
    const { result } = renderHook(() => useRealtimeEvents({ maxEvents }));

    // Wait for connection
    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });

    // Send more events than the buffer limit
    for (let i = 1; i <= 10; i++) {
      const testEvent = {
        id: `evt-${i}`,
        type: 'system' as const,
        title: `Event ${i}`,
        description: `Description ${i}`,
        timestamp: Date.now() + i,
        severity: 'low' as const,
      };
      eventSourceInstance?.simulateMessage(testEvent);
    }

    await waitFor(() => {
      expect(result.current.events.length).toBe(maxEvents);
    });

    // Verify newest events are kept (evt-10 should be first, evt-6 should be last)
    expect(result.current.events[0].id).toBe('evt-10');
    expect(result.current.events[4].id).toBe('evt-6');
  });

  it('cleans up EventSource on unmount', async () => {
    const { result, unmount } = renderHook(() => useRealtimeEvents());

    // Wait for connection
    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });

    const closeSpy = vi.spyOn(eventSourceInstance!, 'close');

    // Unmount the hook
    unmount();

    // Verify EventSource was closed
    expect(closeSpy).toHaveBeenCalled();
    expect(eventSourceInstance?.readyState).toBe(MockEventSource.prototype.CLOSED);
  });

  it('handles invalid JSON in event data gracefully', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useRealtimeEvents());

    // Wait for connection
    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });

    // Simulate receiving invalid JSON
    if (eventSourceInstance?.onmessage) {
      const invalidEvent = new MessageEvent('message', {
        data: 'not valid json',
      });
      eventSourceInstance.onmessage(invalidEvent);
    }

    // Should not crash, events array should remain empty
    expect(result.current.events).toHaveLength(0);
    expect(result.current.connectionState).toBe('connected');
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('Failed to parse event data'),
      expect.any(Error),
      'not valid json'
    );

    consoleSpy.mockRestore();
  });

  it('skips events with missing required fields', async () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { result } = renderHook(() => useRealtimeEvents());

    // Wait for connection
    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });

    // Send event missing required fields
    const invalidEvent = {
      // Missing: id, type, title
      description: 'Test description',
      timestamp: Date.now(),
      severity: 'low',
    };

    eventSourceInstance?.simulateMessage(invalidEvent);

    // Event should be skipped
    expect(result.current.events).toHaveLength(0);
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Received malformed event'),
      expect.any(String)
    );

    consoleWarnSpy.mockRestore();
  });

  it('uses custom endpoint when provided', () => {
    const customEndpoint = '/custom/events/stream';
    renderHook(() => useRealtimeEvents({ endpoint: customEndpoint }));

    expect(global.EventSource).toHaveBeenCalledWith(customEndpoint);
  });

  it('respects enabled flag', () => {
    const { result } = renderHook(() => useRealtimeEvents({ enabled: false }));

    expect(result.current.loading).toBe(false);
    expect(result.current.connectionState).toBe('disconnected');
    expect(global.EventSource).not.toHaveBeenCalled();
  });
});
