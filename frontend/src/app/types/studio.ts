export type SessionKind = 'owner' | 'guest';
export type DocumentKind = 'chapter' | 'outline' | 'character' | 'world' | 'note';
export type SaveState = 'idle' | 'saving' | 'saved' | 'conflict' | 'error';
export type ExportFormat = 'markdown' | 'docx' | 'epub';
export type StudioJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'interrupted';
export type StudioJobKind = 'proposal' | 'review' | 'export';
export type StudioJobOperation = 'continue' | 'rewrite' | 'generate' | 'review' | 'export';

export interface Session {
  session_id: string;
  kind: SessionKind;
  owner_id: string | null;
  expires_at: string | null;
}

export interface SetupStatus {
  owner_configured: boolean;
  version: string;
}

export interface StudioDocument {
  id: string;
  project_id: string;
  kind: DocumentKind;
  title: string;
  position: number;
  current_revision_id: string;
  content_markdown: string;
  metadata: Record<string, unknown>;
  revision_source: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  title: string;
  description: string;
  settings: Record<string, unknown>;
  import_hash: string | null;
  created_at: string;
  updated_at: string;
  documents?: StudioDocument[];
}

export interface Revision {
  id: string;
  document_id: string;
  parent_revision_id: string | null;
  revision_number: number;
  content_markdown: string;
  metadata: Record<string, unknown>;
  source: string;
  word_count: number;
  created_at: string;
}

export interface ReviewIssue {
  id: string;
  document_id: string | null;
  severity: 'blocker' | 'warning' | 'suggestion';
  code: string;
  message: string;
  suggestion: string;
  evidence: Record<string, unknown>;
}

export interface Review {
  id: string;
  project_id: string;
  snapshot_id: string;
  provider: string;
  model: string;
  summary: string;
  created_at: string;
  issues: ReviewIssue[];
}

export interface StudioJobEvent {
  id: string;
  status: StudioJobStatus;
  details: Record<string, unknown>;
  created_at: string;
}

export interface StudioJob {
  id: string;
  project_id: string;
  document_id: string | null;
  kind: StudioJobKind;
  operation: StudioJobOperation;
  status: StudioJobStatus;
  provider: string;
  model: string;
  request: Record<string, unknown>;
  result: {
    proposal_markdown?: string;
    base_revision_id?: string;
    accepted_revision_id?: string | null;
  };
  error: string | null;
  retry_of_job_id: string | null;
  events: StudioJobEvent[];
  created_at: string;
  updated_at: string;
}

export interface StudioExport {
  id: string;
  project_id: string;
  snapshot_id: string;
  format: ExportFormat;
  size_bytes: number;
  checksum_sha256: string;
  created_at: string;
  download_url: string;
}
