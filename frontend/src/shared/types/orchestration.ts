/**
 * Orchestration Types
 */

export interface OrchestrationState {
  status: OrchestrationStatus;
  currentPhase: PipelinePhase;
  activeAgents: AgentStatus[];
  pendingDecision?: DecisionPoint;
  metrics: OrchestrationMetrics;
}

export interface OrchestrationStartRequest {
  character_names: string[];
  turns?: number;
  setting?: string;
  scenario?: string;
}

export type OrchestrationStatus = 'idle' | 'running' | 'paused' | 'waiting_decision' | 'error';

export type PipelinePhase =
  | 'idle'
  | 'context_gathering'
  | 'planning'
  | 'execution'
  | 'synthesis'
  | 'output';

export interface AgentStatus {
  id: string;
  name: string;
  type: 'persona' | 'director' | 'synthesizer';
  status: 'idle' | 'thinking' | 'acting' | 'waiting';
  currentTask?: string;
  lastUpdate: string;
}

export interface DecisionPoint {
  id: string;
  type: 'narrative_branch' | 'conflict_resolution' | 'character_action' | 'world_event';
  prompt: string;
  options: DecisionOption[];
  context: string;
  urgency: 'low' | 'medium' | 'high';
  expiresAt?: string;
}

export interface DecisionOption {
  id: string;
  label: string;
  description: string;
  consequences?: string;
  recommended?: boolean;
}

export interface OrchestrationMetrics {
  turnsCompleted: number;
  totalTokens: number;
  averageLatency: number;
  decisionsResolved: number;
  errorsEncountered: number;
}

export interface OrchestrationEvent {
  id: string;
  type: OrchestrationEventType;
  timestamp: string;
  data: unknown;
}

export type OrchestrationEventType =
  | 'phase_change'
  | 'agent_update'
  | 'decision_required'
  | 'decision_resolved'
  | 'narrative_output'
  | 'error'
  | 'heartbeat';

export interface CommandInput {
  type: 'advance_turn' | 'pause' | 'resume' | 'decide' | 'override';
  payload?: unknown;
}

export interface NarrativeOutput {
  id: string;
  turnNumber: number;
  content: string;
  characters: string[];
  events: string[];
  timestamp: string;
}
