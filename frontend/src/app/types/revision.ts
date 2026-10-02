import type { RevisionSource } from "./studio";

/**
 * DR-011: the single-revision content read (`GET
 * /api/projects/:projectId/documents/:documentId/revisions/:revisionId`).
 * A hand-written response view validated at runtime by
 * `parseRevisionDetail` — the immutable body plus the summary invariants
 * `RevisionSummary` (`types/studio.ts`) already carries.
 */
export interface RevisionDetail {
  id: string;
  document_id: string;
  parent_revision_id: string | null;
  revision_number: number;
  content_markdown: string;
  metadata: Record<string, unknown>;
  source: RevisionSource;
  word_count: number;
  created_at: string;
}
