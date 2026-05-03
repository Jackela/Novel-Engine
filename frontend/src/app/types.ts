export type SessionKind = 'guest' | 'user';
export type WorkspaceKind = 'guest' | 'user' | 'unknown';
export type WorkspacePersistence = 'ephemeral' | 'persistent' | 'unknown';
export type StorySurfaceView = 'workspace' | 'playback';

export interface SessionUser {
  id: string;
  name: string;
  email?: string;
}

export interface ActiveWorkspaceSummary {
  workspaceId: string;
  workspaceKind: WorkspaceKind;
  label: string;
  persistence: WorkspacePersistence;
  summary: string;
}

export interface SessionState {
  id: string;
  kind: SessionKind;
  workspaceId: string;
  token?: string;
  refreshToken?: string;
  user?: SessionUser;
  identityKind?: SessionKind;
  activeWorkspace?: ActiveWorkspaceSummary;
  lastStoryId?: string | null;
  lastRunId?: string | null;
  lastView?: StorySurfaceView;
  createdAt?: string;
  updatedAt?: string;
}

export interface SessionCatalog {
  version: number;
  activeSessionId: string | null;
  sessions: SessionState[];
}

export interface GuestSessionRequest {
  workspace_id?: string | null;
}

export interface GuestSessionResponse {
  workspace_id: string;
  created?: boolean;
  identity_kind?: SessionKind;
  workspace_kind?: WorkspaceKind;
  active_workspace?: {
    workspace_id: string;
    workspace_kind: WorkspaceKind;
    label: string;
    persistence: WorkspacePersistence;
    summary: string;
  };
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
  identity_kind?: SessionKind;
  workspace_kind?: WorkspaceKind;
  active_workspace?: {
    workspace_id: string;
    workspace_kind: WorkspaceKind;
    label: string;
    persistence: WorkspacePersistence;
    summary: string;
  };
  user: SessionUser;
}

export interface CurrentUserResponse {
  id: string;
  username: string;
  email: string;
  roles: string[];
}

export type StoryGenre =
  | 'fantasy'
  | 'sci-fi'
  | 'mystery'
  | 'romance'
  | 'horror'
  | 'adventure'
  | 'historical'
  | 'thriller'
  | 'comedy'
  | 'drama';

export type StoryStatus = 'draft' | 'active' | 'completed';
export type StoryProviderName = 'mock' | 'dashscope' | 'openai_compatible';
export type StorySceneType =
  | 'opening'
  | 'narrative'
  | 'dialogue'
  | 'action'
  | 'decision'
  | 'climax'
  | 'ending';
export type StoryReviewSeverity = 'info' | 'warning' | 'blocker';
export type StoryRunMode = 'manual' | 'pipeline';
export type StoryRunStatus = 'running' | 'completed' | 'failed';
export type StoryRunStageStatus = 'running' | 'completed' | 'failed';
export type StoryRunEventType =
  | 'run_started'
  | 'stage_started'
  | 'stage_completed'
  | 'stage_failed'
  | 'run_completed'
  | 'run_failed';
export type StoryRunSnapshotType =
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
export type StoryArtifactKind =
  | 'blueprint'
  | 'outline'
  | 'review'
  | 'semantic_review'
  | 'hybrid_review'
  | 'draft_failure'
  | 'export';
export type StoryNarrativeStrand = 'quest' | 'fire' | 'constellation';

export interface StoryScene {
  id: string;
  chapter_id: string;
  scene_number: number;
  title: string | null;
  content: string;
  scene_type: StorySceneType;
  choices: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StoryChapter {
  id: string;
  story_id: string;
  chapter_number: number;
  title: string;
  summary: string | null;
  scenes: StoryScene[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StoryMemoryChapterSummary {
  chapter_number: number;
  title: string;
  summary: string;
  focus_character: string;
  focus_motivation: string;
  hook: string;
}

export interface StoryTimelineLedgerEntry {
  chapter_number: number;
  timeline_day: number;
  summary: string;
}

export interface StoryHookLedgerEntry {
  chapter_number: number;
  hook: string;
  surfaced: boolean;
}

export interface StoryPromise {
  promise_id: string;
  chapter_number: number;
  text: string;
  strand: string;
  chapter_objective: string;
  due_by_chapter: number | null;
}

export interface StoryPromiseLedgerEntry {
  chapter_number: number;
  promise: string;
  surfaced: boolean;
  promise_id: string;
  strand: string;
  chapter_objective: string;
  payoff_chapter: number | null;
  due_by_chapter: number | null;
  status: string;
}

export interface StoryPayoffBeat {
  promise_id: string;
  chapter_number: number;
  payoff_text: string;
  strength: number;
}

export interface StoryPacingLedgerEntry {
  chapter_number: number;
  phase: string;
  signature: string;
  tension: number;
  hook_strength: number;
  chapter_objective: string;
}

export interface StoryStrandLedgerEntry {
  chapter_number: number;
  strand: string;
  status: string;
}

export interface StoryCharacterStateSnapshot {
  chapter_number: number;
  name: string;
  motivation: string;
  role: string;
}

export interface StoryRelationshipSnapshot {
  chapter_number: number;
  source: string;
  target: string;
  status: string;
}

export interface StoryWorldRuleLedgerEntry {
  rule: string;
  source: string;
}

export interface StoryMemory {
  schema_version?: number;
  premise: string;
  tone: string;
  target_chapters: number;
  themes: string[];
  chapter_summaries: StoryMemoryChapterSummary[];
  active_characters: string[];
  outline_titles: string[];
  story_promises: StoryPromise[];
  timeline_ledger: StoryTimelineLedgerEntry[];
  hook_ledger: StoryHookLedgerEntry[];
  promise_ledger: StoryPromiseLedgerEntry[];
  payoff_beats: StoryPayoffBeat[];
  pacing_ledger: StoryPacingLedgerEntry[];
  strand_ledger: StoryStrandLedgerEntry[];
  character_states: StoryCharacterStateSnapshot[];
  relationship_states: StoryRelationshipSnapshot[];
  world_rules: StoryWorldRuleLedgerEntry[];
  revision_notes: string[];
}

export interface StoryBlueprint {
  step: string;
  provider: StoryProviderName;
  model: string;
  generated_at: string;
  story_id: string;
  version: number;
  world_bible: Record<string, unknown>;
  character_bible: Record<string, unknown>;
  premise_summary: string;
}

export interface StoryOutlineChapter {
  chapter_number: number;
  title: string;
  summary: string;
  hook: string;
  promise: string;
  pacing_phase: string;
  narrative_strand: string;
  chapter_objective: string;
  primary_strand: string;
  secondary_strand: string | null;
  promised_payoff: string;
  hook_strength: number;
}

export interface StoryOutline {
  step: string;
  provider: StoryProviderName;
  model: string;
  generated_at: string;
  target_chapters: number;
  version: number;
  chapters: StoryOutlineChapter[];
}

export interface StoryReviewIssue {
  code: string;
  severity: StoryReviewSeverity;
  message: string;
  location: string | null;
  suggestion: string | null;
  details: Record<string, unknown>;
}

export interface StoryReviewReport {
  artifact_id: string;
  version: number;
  source_run_id: string | null;
  source_provider: string;
  source_model: string;
  story_id: string;
  quality_score: number;
  ready_for_publish: boolean;
  summary: string;
  issues: StoryReviewIssue[];
  revision_notes: string[];
  chapter_count: number;
  scene_count: number;
  continuity_checks: Record<string, boolean>;
  checked_at: string;
  metrics: {
    continuity_score: number;
    pacing_score: number;
    hook_score: number;
    character_consistency_score: number;
    timeline_consistency_score: number;
  };
}

export interface StorySemanticReviewReport {
  artifact_id: string;
  version: number;
  source_run_id: string | null;
  source_provider: StoryProviderName;
  source_model: string;
  story_id: string;
  semantic_score: number;
  ready_for_publish: boolean;
  summary: string;
  issues: StoryReviewIssue[];
  repair_suggestions: string[];
  checked_at: string;
  metrics: {
    semantic_score: number;
    reader_pull_score: number;
    plot_clarity_score: number;
    ooc_risk_score: number;
  };
}

export interface DraftFailureArtifact {
  story_id: string;
  stage_name: string;
  chapter_number: number;
  failure_code: string;
  failure_message: string;
  raw_text: string;
  raw_payload: Record<string, unknown>;
  normalized_payload: Record<string, unknown>;
  validation_errors: string[];
  artifact_id: string;
  version: number;
  generated_at: string;
  source_run_id: string | null;
  source_provider: string;
  source_model: string;
}

export interface StoryHybridReviewReport {
  artifact_id: string;
  version: number;
  source_run_id: string | null;
  source_provider: string;
  source_model: string;
  story_id: string;
  quality_score: number;
  ready_for_publish: boolean;
  summary: string;
  structural_review: StoryReviewReport | null;
  semantic_review: StorySemanticReviewReport | null;
  issues: StoryReviewIssue[];
  blocked_by: string[];
  structural_gate_passed?: boolean;
  semantic_gate_passed?: boolean;
  publish_gate_passed?: boolean;
  checked_at: string;
}

export interface StoryExportPayload {
  artifact_id: string;
  version: number;
  source_run_id: string | null;
  source_provider: string;
  source_model: string;
  story: StorySnapshot;
  workflow: StoryWorkflowState;
  memory: StoryMemory;
  blueprint: StoryBlueprint | null;
  outline: StoryOutline | null;
  last_review: StoryReviewReport | null;
  revision_notes: string[];
  exported_at: string;
}

export interface StoryGenerationTraceEntry {
  timestamp: string;
  step: string;
  provider: StoryProviderName;
  model: string;
  content_keys: string[];
}

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

export interface StoryRunSnapshot {
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
  workspace: StoryWorkspace;
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

export interface StoryWorkflowState {
  schema_version?: number;
  status: string;
  premise: string;
  tone: string;
  target_chapters: number;
  generation_trace: StoryGenerationTraceEntry[];
  chapter_memory: StoryMemoryChapterSummary[];
  revision_notes: string[];
  blueprint: StoryBlueprint | null;
  blueprint_generated_at: string | null;
  outline: StoryOutline | null;
  outline_generated_at: string | null;
  drafted_chapters: number;
  last_structural_review: StoryReviewReport | null;
  last_semantic_review: StorySemanticReviewReport | null;
  last_review: StoryHybridReviewReport | null;
  last_exported_at: string | null;
  last_updated_at: string | null;
  published_at: string | null;
  revision_history: Array<Record<string, unknown>>;
  run_state: StoryRunState | null;
  current_run_id?: string | null;
}

export interface StoryMetadata extends Record<string, unknown> {
  workflow?: StoryWorkflowState;
  story_memory?: StoryMemory;
  world_bible?: Record<string, unknown>;
  character_bible?: Record<string, unknown>;
  premise_summary?: string;
}

export interface StorySnapshot {
  id: string;
  title: string;
  genre: StoryGenre | string;
  author_id: string;
  status: StoryStatus | string;
  chapters: StoryChapter[];
  chapter_count: number;
  current_chapter_id: string | null;
  target_audience: string | null;
  themes: string[];
  metadata: StoryMetadata;
  created_at: string;
  updated_at: string;
}

export interface StoryWorkspace {
  story: StorySnapshot;
  workflow: StoryWorkflowState;
  memory: StoryMemory;
  blueprint: StoryBlueprint | null;
  outline: StoryOutline | null;
  structural_review: StoryReviewReport | null;
  semantic_review: StorySemanticReviewReport | null;
  hybrid_review: StoryHybridReviewReport | null;
  review: StoryHybridReviewReport | null;
  export: StoryExportPayload | null;
  revision_notes: string[];
  run: StoryRunState | null;
  run_history: StoryRunState[];
  run_events: StoryRunEvent[];
  artifact_history: StoryArtifactHistoryEntry[];
  workspace_context?: {
    workspace_id: string;
    workspace_kind: WorkspaceKind;
    author_id: string;
    label: string;
    summary: string;
  };
  recommended_next_action?: {
    action: string;
    label: string;
    reason: string;
    target_view: StorySurfaceView;
  };
  evidence_summary?: {
    warning_count: number;
    blocker_count: number;
    zero_warning: boolean;
    published: boolean;
    publish_gate_passed: boolean;
    has_export: boolean;
    latest_run_id: string | null;
    artifact_count: number;
  };
}

export interface StoryListResponse {
  stories: StorySnapshot[];
  count: number;
  limit: number;
  offset: number;
}

export interface StoryCreateRequest {
  title: string;
  genre: StoryGenre;
  premise: string;
  target_chapters: number;
  target_audience?: string | null;
  themes?: string[];
  tone?: string;
  author_id?: string | null;
}

export interface StoryPipelineRequest extends StoryCreateRequest {
  publish: boolean;
}

export interface StoryRunRequest {
  operation: StoryRunOperation;
  target_chapters?: number | null;
  publish?: boolean;
}

export interface StoryCreateResponse {
  story: StorySnapshot;
}

export interface StoryBlueprintResponse {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  blueprint: StoryBlueprint;
}

export interface StoryOutlineResponse {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  outline: StoryOutline;
}

export interface StoryDraftResponse {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  drafted_chapters: number;
  skipped?: boolean;
}

export interface StoryReviewResponse {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  report: StoryHybridReviewReport;
}

export interface StoryReviseResponse {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  report: StoryHybridReviewReport;
  revision_notes: string[];
}

export interface StoryExportResponse {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  export: StoryExportPayload;
}

export interface StoryPublishResponse {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  report: StoryHybridReviewReport;
}

export interface StoryPipelineResult {
  story: StorySnapshot;
  workspace: StoryWorkspace;
  blueprint: StoryBlueprint;
  outline: StoryOutline;
  drafted_chapters: number;
  initial_review: StoryHybridReviewReport;
  revision_notes: string[];
  final_review: StoryHybridReviewReport;
  export: StoryExportPayload;
  published: boolean;
}

export interface StoryWorkspaceResponse {
  workspace: StoryWorkspace;
}

export interface StoryRunsResponse {
  current_run: StoryRunState | null;
  runs: StoryRunState[];
}

export interface StoryRunDetailResponse {
  operation?: StoryRunOperation;
  run: StoryRunState;
  events: StoryRunEvent[];
  artifacts: StoryArtifactHistoryEntry[];
  latest_snapshot: StoryRunSnapshot | null;
  stage_snapshots: StoryRunSnapshot[];
  provenance?: {
    run_id: string;
    mode: StoryRunMode;
    story_id: string;
    started_at: string;
    completed_at: string | null;
    source_providers: string[];
    source_models: string[];
    snapshot_captured_at: string | null;
  };
  publish_verdict?: {
    published: boolean;
    ready_for_publish: boolean;
    publish_gate_passed: boolean;
    warning_count: number;
    blocker_count: number;
    checked_at: string | null;
  };
  evidence_status?: {
    has_latest_snapshot: boolean;
    stage_snapshot_count: number;
    artifact_count: number;
    failure_artifact_count: number;
    zero_warning: boolean;
  };
  failed_stage?: string | null;
  failure_code?: string | null;
  failure_message?: string | null;
  failure_snapshot?: StoryRunSnapshot | null;
  failure_artifacts?: StoryArtifactHistoryEntry[];
  manuscript_preserved?: boolean | null;
}

export interface StoryArtifactsResponse {
  current: {
    blueprint: StoryBlueprint | null;
    outline: StoryOutline | null;
    structural_review: StoryReviewReport | null;
    semantic_review: StorySemanticReviewReport | null;
    review: StoryHybridReviewReport | null;
    export: StoryExportPayload | null;
  };
  history: StoryArtifactHistoryEntry[];
}
