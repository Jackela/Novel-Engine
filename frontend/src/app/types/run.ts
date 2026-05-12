export type StoryRunMode = 'manual' | 'pipeline';
type StoryRunStatus = 'running' | 'completed' | 'failed';
type StoryRunStageStatus = 'running' | 'completed' | 'failed';
type StoryRunEventType =
  | 'run_started'
  | 'stage_started'
  | 'stage_completed'
  | 'stage_failed'
  | 'run_completed'
  | 'run_failed';
type StoryRunSnapshotType =
  | 'run_started'
  | 'stage_completed'
  | 'run_completed'
  | 'run_failed';
export type StoryRunOperation =
  | 'blueprint'
  | 'outline'
  | 'draft'
  | 'review'
  | 'revise'
  | 'export'
  | 'publish'
  | 'pipeline';
type StoryArtifactKind =
  | 'blueprint'
  | 'outline'
  | 'review'
  | 'semantic_review'
  | 'hybrid_review'
  | 'draft_failure'
  | 'export';

export interface StoryRunStageExecution {
  name: string;
  status: StoryRunStageStatus;
  started_at: string;
  completed_at: string | null;
  failure_code: string | null;
  failure_message: string | null;
  details: Record<string, unknown>;
}

export interface StoryRunState {
  run_id: string;
  mode: StoryRunMode;
  status: StoryRunStatus;
  started_at: string;
  completed_at: string | null;
  published: boolean;
  stages: StoryRunStageExecution[];
}

export interface StoryRunEvent {
  event_id: string;
  run_id: string;
  event_type: StoryRunEventType;
  timestamp: string;
  stage_name: string | null;
  details: Record<string, unknown>;
}

export interface StoryRunSnapshot<TWorkspace = unknown> {
  snapshot_id: string;
  story_id: string;
  run_id: string;
  snapshot_type: StoryRunSnapshotType;
  captured_at: string;
  stage_name: string | null;
  failed_stage?: string | null;
  failure_code?: string | null;
  failure_message?: string | null;
  failure_details?: Record<string, unknown>;
  workspace: TWorkspace;
}

export interface StoryArtifactHistoryEntry {
  artifact_id: string;
  kind: StoryArtifactKind;
  version: number;
  generated_at: string;
  source_run_id: string | null;
  source_stage: string;
  source_provider: string;
  source_model: string;
  parent_artifact_ids: string[];
  payload: Record<string, unknown>;
}
