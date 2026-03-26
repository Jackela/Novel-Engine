import { startTransition, useEffect, useState } from 'react';

import { appConfig } from '@/app/config';
import type { DashboardEvent } from '@/app/types';

function parseEventPayload(raw: string): DashboardEvent | null {
  try {
    return JSON.parse(raw) as DashboardEvent;
  } catch {
    return null;
  }
}

export function useDashboardEvents(workspaceId: string) {
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [connectionState, setConnectionState] = useState<
    'connecting' | 'connected' | 'disconnected'
  >('connecting');

  useEffect(() => {
    if (!workspaceId) {
      return;
    }

    const target = `${appConfig.apiBaseUrl}${appConfig.endpoints.eventsStream}?workspace_id=${encodeURIComponent(workspaceId)}`;
    let eventSource: EventSource | null = null;

    const appendEvents = (nextEvents: DashboardEvent[]) => {
      startTransition(() => {
        setEvents((current) => [...nextEvents, ...current].slice(0, 10));
      });
    };

    try {
      setEvents([]);
      setConnectionState('connecting');
      eventSource = new EventSource(target, { withCredentials: true });
      eventSource.onopen = () => {
        setConnectionState('connected');
      };
      eventSource.onmessage = (event) => {
        const payload = parseEventPayload(event.data);
        if (payload) {
          appendEvents([payload]);
        }
      };
      eventSource.onerror = () => {
        setConnectionState('disconnected');
      };
    } catch {
      setConnectionState('disconnected');
    }

    return () => {
      eventSource?.close();
    };
  }, [workspaceId]);

  return { events, connectionState };
}
