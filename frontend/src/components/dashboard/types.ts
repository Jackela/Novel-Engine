export type OrchestrationStatus = 'idle' | 'running' | 'paused' | 'stopped';

export interface RunStateSummary {
  status: OrchestrationStatus;
  mode: 'live' | 'simulation';
  connected: boolean;
  isLiveMode: boolean;
  phase?: string;
  lastUpdated?: number;
  lastAction?: string;
}

export type QuickAction =
  | 'play'
  | 'pause'
  | 'stop'
  | 'refresh'
  | 'save'
  | 'settings'
  | 'fullscreen'
  | 'export';
