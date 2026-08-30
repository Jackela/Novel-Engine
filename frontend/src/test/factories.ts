import type {
  Project,
  Review,
  Revision,
  StudioDocument,
  StudioExport,
  StudioJob,
  Volume,
} from "@/app/types/studio";

/**
 * Shared test fixture builders (#410). Every builder takes an id plus a
 * partial overrides object so a test only names the fields it actually
 * cares about; `vi.mock` declarations stay inside each test file because
 * `vi.mock` hoisting is file-local — share the mock *shapes*, not the mocks.
 */

const FIXTURE_TIMESTAMP = "2026-08-27T00:00:00Z";

export function chapter(id: string, overrides: Partial<StudioDocument> = {}): StudioDocument {
  return {
    id,
    project_id: "project-1",
    kind: "chapter",
    title: `Titled ${id}`,
    position: 0,
    volume_id: "volume-1",
    current_revision_id: `revision-${id}`,
    content_markdown: "",
    metadata: {},
    revision_source: "author",
    word_count: 0,
    created_at: FIXTURE_TIMESTAMP,
    updated_at: FIXTURE_TIMESTAMP,
    ...overrides,
  };
}

export function project(overrides: Partial<Project> = {}): Project {
  return {
    id: "project-1",
    title: "Clockwork Harbor",
    description: "",
    settings: {},
    import_hash: null,
    created_at: FIXTURE_TIMESTAMP,
    updated_at: FIXTURE_TIMESTAMP,
    documents: [],
    ...overrides,
  };
}

export function projectWith(
  documents: StudioDocument[],
  overrides: Partial<Project> = {},
): Project {
  return project({ ...overrides, documents });
}

export function revision(id: string, overrides: Partial<Revision> = {}): Revision {
  return {
    id,
    document_id: "document-1",
    parent_revision_id: null,
    revision_number: 1,
    content_markdown: "Draft",
    metadata: {},
    source: "manual",
    word_count: 1,
    created_at: FIXTURE_TIMESTAMP,
    ...overrides,
  };
}

export function volume(id: string, position: number, overrides: Partial<Volume> = {}): Volume {
  return {
    id,
    project_id: "project-1",
    title: id,
    position,
    created_at: FIXTURE_TIMESTAMP,
    updated_at: FIXTURE_TIMESTAMP,
    ...overrides,
  };
}

export function review(overrides: Partial<Review> = {}): Review {
  return {
    id: "review-1",
    project_id: "project-1",
    snapshot_id: "snapshot-1",
    provider: "mock",
    model: "studio-copilot-v1",
    summary: "Looks good.",
    created_at: FIXTURE_TIMESTAMP,
    issues: [],
    ...overrides,
  };
}

export function studioExport(overrides: Partial<StudioExport> = {}): StudioExport {
  return {
    id: "export-1",
    project_id: "project-1",
    snapshot_id: "snapshot-1",
    format: "markdown",
    size_bytes: 128,
    checksum_sha256: "checksum-1",
    created_at: FIXTURE_TIMESTAMP,
    download_url: "/downloads/export-1",
    ...overrides,
  };
}

export function job(overrides: Partial<StudioJob> = {}): StudioJob {
  return {
    id: "job-1",
    project_id: "project-1",
    document_id: "document-1",
    kind: "proposal",
    operation: "continue",
    status: "completed",
    provider: "mock",
    model: "studio-copilot-v1",
    request: {},
    result: {},
    error: null,
    retry_of_job_id: null,
    events: [],
    created_at: FIXTURE_TIMESTAMP,
    updated_at: FIXTURE_TIMESTAMP,
    ...overrides,
  };
}
