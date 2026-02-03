/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_TIMEOUT?: string;
  readonly VITE_ENABLE_GUEST_MODE?: string;
  readonly VITE_DASHBOARD_EVENTS_ENDPOINT?: string;
  readonly VITE_DASHBOARD_CHARACTERS_ENDPOINT?: string;
  readonly VITE_DASHBOARD_DEBUG?: string;
  readonly VITE_SHOW_PERFORMANCE_METRICS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Window {
  __REDUX_STORE__?: {
    dispatch: (action: { type: string; payload?: unknown }) => void;
    getState: () => {
      decision: {
        currentDecision: unknown;
        pauseState: string;
        selectedOptionId: number | null;
        freeTextInput: string;
        remainingSeconds: number;
      };
    };
  };
}
