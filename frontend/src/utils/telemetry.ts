export type TelemetryEvent = {
  type: string;
  payload: Record<string, unknown>;
};

declare global {
  interface Window {
    __novelEngineTelemetry?: {
      emit: (event: TelemetryEvent) => void;
      subscribe?: (listener: (event: TelemetryEvent) => void) => () => void;
    };
  }
}

const noopDispatcher = { emit: (_event: TelemetryEvent) => {} };

function ensureDispatcher() {
  if (typeof window === 'undefined') return noopDispatcher;

  if (!window.__novelEngineTelemetry) {
    const listeners: ((event: TelemetryEvent) => void)[] = [];
    window.__novelEngineTelemetry = {
      emit: (event: TelemetryEvent) => {
        listeners.forEach((listener) => listener(event));
      },
    };
    window.__novelEngineTelemetry.subscribe = (listener: (event: TelemetryEvent) => void) => {
      listeners.push(listener);
      return () => {
        const index = listeners.indexOf(listener);
        if (index >= 0) listeners.splice(index, 1);
      };
    };
  }

  return window.__novelEngineTelemetry;
}

export const telemetry = {
  emit(event: TelemetryEvent) {
    ensureDispatcher().emit(event);
  },
};

export type TelemetrySubscribe = (event: TelemetryEvent) => void;

export function subscribe(listener: TelemetrySubscribe): () => void {
  const dispatcher = ensureDispatcher();
  if (dispatcher.subscribe) {
    return dispatcher.subscribe(listener);
  }
  return () => {};
}
