import { act } from 'react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';

import { screen, render, cleanup } from '../../tests/test-utils';
import { useDashboardEvents } from './useDashboardEvents';

type StreamEventType = 'open' | 'error' | 'system' | 'orchestration' | 'signal';

class MockEventSource {
  static instances: MockEventSource[] = [];

  readonly url: string;

  readonly withCredentials: boolean;

  readonly close = vi.fn();

  onopen: ((event: Event) => void) | null = null;

  onerror: ((event: Event) => void) | null = null;

  onmessage: ((event: MessageEvent<string>) => void) | null = null;

  private readonly listeners = new Map<string, Set<(event: Event) => void>>();

  constructor(url: string, init?: EventSourceInit) {
    this.url = url;
    this.withCredentials = Boolean(init?.withCredentials);
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: Event) => void): void {
    const listeners = this.listeners.get(type) ?? new Set();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: (event: Event) => void): void {
    this.listeners.get(type)?.delete(listener);
  }

  emit(type: StreamEventType, data = ''): void {
    const event = type === 'open' || type === 'error' ? new Event(type) : new MessageEvent(type, { data });

    if (type === 'open') {
      this.onopen?.(event);
    } else if (type === 'error') {
      this.onerror?.(event);
    } else if (type === 'signal' || type === 'system' || type === 'orchestration') {
      this.listeners.get(type)?.forEach((listener) => listener(event));
    }
  }
}

const originalEventSource = globalThis.EventSource;

function DashboardEventsProbe({ workspaceId }: { workspaceId: string }) {
  const { events, connectionState } = useDashboardEvents(workspaceId);

  return (
    <section>
      <div data-testid="connection-state">{connectionState}</div>
      <div data-testid="event-count">{events.length}</div>
      <ul data-testid="event-titles">
        {events.map((event) => (
          <li key={event.id}>{event.title}</li>
        ))}
      </ul>
    </section>
  );
}

beforeEach(() => {
  MockEventSource.instances = [];
  Object.defineProperty(globalThis, 'EventSource', {
    configurable: true,
    writable: true,
    value: MockEventSource,
  });
});

afterEach(() => {
  Object.defineProperty(globalThis, 'EventSource', {
    configurable: true,
    writable: true,
    value: originalEventSource,
  });
  cleanup();
});

test('subscribes to named SSE events and appends dashboard updates', async () => {
  render(<DashboardEventsProbe workspaceId="workspace-123" />);

  const source = MockEventSource.instances[0];
  if (!source) {
    throw new Error('Expected EventSource instance to be created.');
  }

  expect(source).toBeDefined();
  expect(source.url).toContain('workspace_id=workspace-123');
  expect(source.withCredentials).toBe(true);

  await act(async () => {
    source.emit('open');
  });

  expect(screen.getByTestId('connection-state')).toHaveTextContent('connected');

  await act(async () => {
    source.emit(
      'system',
      JSON.stringify({
        id: 'event-system',
        type: 'system',
        title: 'Heartbeat',
        description: 'Dashboard connection is alive',
        timestamp: '2026-03-26T12:00:00Z',
        workspace_id: 'workspace-123',
      }),
    );
  });

  await act(async () => {
    source.emit(
      'orchestration',
      JSON.stringify({
        id: 'event-orchestration',
        type: 'orchestration',
        title: 'Orchestration started',
        description: 'Canonical runtime orchestration has started.',
        timestamp: '2026-03-26T12:00:05Z',
        workspace_id: 'workspace-123',
      }),
    );
  });

  expect(await screen.findByText('Heartbeat')).toBeInTheDocument();
  expect(screen.getByText('Orchestration started')).toBeInTheDocument();
  expect(screen.getByTestId('event-count')).toHaveTextContent('2');
});
