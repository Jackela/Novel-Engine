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
export type StorySceneType =
  | 'opening'
  | 'narrative'
  | 'dialogue'
  | 'action'
  | 'decision'
  | 'climax'
  | 'ending';
export type StoryReviewSeverity = 'info' | 'warning' | 'blocker';

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
  summary?: string;
  focus_character?: string;
  hook?: string;
}

export interface StoryMemory extends Record<string, unknown> {
  chapter_summaries?: StoryMemoryChapterSummary[];
  active_characters?: string[];
  outline_titles?: string[];
}

export interface StoryBlueprint {
  step: string;
  provider: string;
  model: string;
  generated_at: string;
  story_id: string;
  world_bible: Record<string, unknown>;
  character_bible: Record<string, unknown>;
  premise_summary: string;
}

export interface StoryOutlineChapter {
  chapter_number: number;
  title: string;
  summary: string;
  hook: string;
}

export interface StoryOutline {
  step: string;
  provider: string;
  model: string;
  generated_at: string;
  target_chapters: number;
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
}

export interface StoryExportPayload {
  story: StorySnapshot;
  workflow: Record<string, unknown>;
  memory: StoryMemory;
  blueprint: StoryBlueprint | null;
  outline: StoryOutline | null;
  last_review: StoryReviewReport | null;
  revision_notes: string[];
}

export interface StoryWorkflowState extends Record<string, unknown> {
  status?: string;
  premise?: string;
  tone?: string;
  target_chapters?: number;
  generation_trace?: Array<Record<string, unknown>>;
  chapter_memory?: Array<Record<string, unknown>>;
  revision_notes?: string[];
  blueprint?: StoryBlueprint;
  blueprint_generated_at?: string;
  outline?: StoryOutline;
  outline_generated_at?: string;
  drafted_chapters?: number;
  last_review?: StoryReviewReport;
  last_exported_at?: string;
  last_updated_at?: string;
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

export interface StoryCreateResponse {
  story: StorySnapshot;
}

export interface StoryBlueprintResponse {
  story: StorySnapshot;
  blueprint: StoryBlueprint;
}

export interface StoryOutlineResponse {
  story: StorySnapshot;
  outline: StoryOutline;
}

export interface StoryDraftResponse {
  story: StorySnapshot;
  drafted_chapters: number;
  skipped?: boolean;
}

export interface StoryReviewResponse {
  story: StorySnapshot;
  report: StoryReviewReport;
}

export interface StoryReviseResponse {
  story: StorySnapshot;
  report: StoryReviewReport;
  revision_notes: string[];
}

export interface StoryExportResponse {
  story: StorySnapshot;
  export: StoryExportPayload;
}

export interface StoryPublishResponse {
  story: StorySnapshot;
  report: StoryReviewReport;
}

export interface StoryPipelineResult {
  story: StorySnapshot;
  blueprint: StoryBlueprint;
  outline: StoryOutline;
  drafted_chapters: number;
  initial_review: StoryReviewReport;
  revision_notes: string[];
  final_review: StoryReviewReport;
  export: StoryExportPayload;
  published: boolean;
}
