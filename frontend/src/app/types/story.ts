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

interface StoryConfig {
  title: string;
  genre: StoryGenre | string;
  premise: string;
  target_chapters: number;
  tone: string;
  target_audience?: string | null;
  themes: string[];
  style_profile?: Record<string, unknown>;
}

export interface WorkspaceCreateRequest {
  workspace_id?: string | null;
  title: string;
  genre: StoryGenre | string;
  premise: string;
  target_chapters: number;
  target_audience?: string | null;
  themes?: string[];
  tone?: string;
  force?: boolean;
}

interface ChapterStatus {
  chapter_number: number;
  filename: string;
  artifact_id: string;
  relative_path: string;
  word_count: number;
  summary: string | null;
  sidecar: Record<string, unknown>;
}

export interface ReviewIssue {
  severity: 'blocker' | 'warning' | 'suggestion' | string;
  code: string;
  message: string;
  location: string;
  suggestion: string;
  details: Record<string, unknown>;
}

interface ReviewReport {
  story_title: string;
  checked_at: string;
  blockers: ReviewIssue[];
  warnings: ReviewIssue[];
  suggestions: ReviewIssue[];
  style_notes: string[];
  export_blocked: boolean;
}

interface RunEvent {
  timestamp: string;
  operation: string;
  status: string;
  details: Record<string, unknown>;
}

interface RunStatus {
  run_id: string;
  artifact_id: string;
  relative_path: string;
  events: RunEvent[];
  artifact_count: number;
  last_event: RunEvent | null;
}

interface ArtifactRef {
  artifact_id: string;
  filename?: string | null;
  relative_path: string;
  size?: number | null;
  run_id?: string | null;
}

type ExportStatus = ArtifactRef;

export type JobOperation = 'draft' | 'run' | 'review' | 'revise' | 'export';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'interrupted';
export type ProviderName = 'mock' | 'dashscope' | 'openai_compatible';

export interface ProviderStatus {
  provider: ProviderName;
  label: string;
  configured: boolean;
  is_default: boolean;
  model: string;
}

export interface ProviderListResponse {
  default_provider: ProviderName;
  providers: ProviderStatus[];
}

export interface WorkspaceJobRequest {
  operation: JobOperation;
  chapter?: number | null;
  target_chapters?: number | null;
  provider?: ProviderName | null;
}

type ArtifactJobResult = {
  result_type: 'artifact';
  artifact: ArtifactRef;
  chapter_number: number;
  provider: string;
  model: string;
  run_id: string;
  sidecar: Record<string, unknown>;
};

type ReviewJobResult = {
  result_type: 'review';
  review: ReviewReport;
};

type RunJobResult = {
  result_type: 'run';
  review: ReviewReport;
  run_id: string;
};

type ExportJobResult = {
  result_type: 'export';
  export: ArtifactRef;
};

type WorkspaceJobResult =
  | ArtifactJobResult
  | ReviewJobResult
  | RunJobResult
  | ExportJobResult;

export interface WorkspaceJob {
  job_id: string;
  workspace_id: string;
  operation: JobOperation;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  provider: ProviderName;
  result: WorkspaceJobResult | null;
  error: string | null;
  failure_artifact: ArtifactRef | null;
  events: Array<{ timestamp: string; status: JobStatus; details: Record<string, unknown> }>;
}

export interface WorkspaceStatus {
  workspace_id: string;
  story: StoryConfig;
  chapters: ChapterStatus[];
  latest_review: ReviewReport | null;
  exports: ExportStatus[];
  runs: RunStatus[];
  jobs: WorkspaceJob[];
}

export interface WorkspaceListResponse {
  workspaces: WorkspaceStatus[];
}
