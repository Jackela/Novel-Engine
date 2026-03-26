export type SessionKind = 'guest' | 'user';

export interface SessionUser {
  id: string;
  name: string;
  email?: string;
}

export interface SessionState {
  kind: SessionKind;
  workspaceId: string;
  token?: string;
  refreshToken?: string;
  user?: SessionUser;
}

export interface GuestSessionResponse {
  workspace_id: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  workspace_id: string;
  user: SessionUser;
}

export type OrchestrationState = 'idle' | 'running' | 'paused' | 'completed';
export type OrchestrationStepState = 'pending' | 'running' | 'completed' | 'failed';

export interface OrchestrationStep {
  id: string;
  name: string;
  status: OrchestrationStepState;
  progress: number;
}

export interface DashboardStatus {
  status: 'healthy' | 'degraded' | 'offline';
  mode: 'remote';
  workspaceId: string;
  headline: string;
  summary: string;
  activeCharacters: number;
  activeSignals: number;
}

export interface OrchestrationStatus {
  status: OrchestrationState;
  current_turn: number;
  total_turns: number;
  queue_length: number;
  average_processing_time: number;
  steps: OrchestrationStep[];
}

export interface DashboardEvent {
  id: string;
  type: 'system' | 'orchestration' | 'signal';
  title: string;
  description: string;
  timestamp: string;
  workspace_id: string;
  data?: Record<string, unknown>;
}

export interface CharacterCardData {
  id: string;
  name: string;
  role: string;
  drive: string;
  region: string;
}

export interface WorldBeat {
  id: string;
  label: string;
  value: string;
  tone: 'neutral' | 'warm' | 'cool';
}
