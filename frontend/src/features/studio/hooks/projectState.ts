import type {
  DocumentSummary,
  LoreStatus,
  Project,
  ProjectListItem,
  StudioDocument,
  Volume,
} from "@/app/types/studio";

export function summarizeDocument(document: StudioDocument): DocumentSummary {
  const { content_markdown: _content, metadata: _metadata, ...summary } = document;
  return summary;
}

/** Merge one document result without letting a stale aggregate replace its siblings. */
export function mergeProjectDocument(project: Project, document: StudioDocument): Project {
  const documents = project.documents;
  if (!documents.some((candidate) => candidate.id === document.id)) return project;
  return {
    ...project,
    documents: documents.map((candidate) =>
      candidate.id === document.id ? summarizeDocument(document) : candidate,
    ),
  };
}

/** Apply only the positions owned by a reorder response. */
export function mergeProjectDocumentOrder(
  project: Project,
  orderedDocuments: readonly DocumentSummary[],
): Project {
  const currentById = new Map(project.documents.map((document) => [document.id, document]));
  const orderedIds = new Set(orderedDocuments.map((document) => document.id));
  const reordered = orderedDocuments.flatMap((ordered) => {
    const current = currentById.get(ordered.id);
    return current ? [{ ...current, position: ordered.position }] : [];
  });
  const remaining = project.documents.filter((document) => !orderedIds.has(document.id));
  return { ...project, documents: [...reordered, ...remaining] };
}

/**
 * Whole-set reorder ids for one Move up/down (#480): the moving document
 * swaps with its neighbor inside the displayed reading group — the same
 * volume for chapters (a missing volume id falls back to the first volume,
 * matching the navigator), the same kind for everything else. The flat
 * position sort used before picked cross-kind or cross-volume neighbors,
 * whose swap leaves every per-volume/per-kind subsequence unchanged, so the
 * server projected the reorder to identical positions. Swapping the two ids
 * in the shell's reading-order array reverses exactly their shared
 * subsequence; null means the document sits at its group edge or is unknown,
 * and no request should be submitted.
 */
export function swapReadingGroupNeighborIds(
  documents: readonly DocumentSummary[],
  volumes: readonly Volume[],
  documentId: string,
  direction: -1 | 1,
): string[] | null {
  const firstVolumeId = volumes[0]?.id;
  const readingGroupOf = (document: DocumentSummary): string =>
    document.kind === "chapter"
      ? `chapter:${document.volume_id ?? firstVolumeId ?? ""}`
      : document.kind;
  const moving = documents.find((document) => document.id === documentId);
  if (moving === undefined) return null;
  const group = readingGroupOf(moving);
  const sameGroup = documents.filter((document) => readingGroupOf(document) === group);
  const index = sameGroup.findIndex((document) => document.id === documentId);
  const neighbor = sameGroup[index + direction];
  if (neighbor === undefined) return null;
  return documents.map((document) =>
    document.id === documentId
      ? neighbor.id
      : document.id === neighbor.id
        ? documentId
        : document.id,
  );
}

/** Apply only fields owned by the project-settings mutation. */
export function mergeProjectSettings(project: Project, updated: ProjectListItem): Project {
  return {
    ...project,
    title: updated.title,
    description: updated.description,
    settings: updated.settings,
    updated_at: updated.updated_at > project.updated_at ? updated.updated_at : project.updated_at,
  };
}

/** One narrow summary field a revision-free command owns exclusively (#466). */
export type NarrowSummaryPatch =
  | { readonly field: "lore_status"; readonly value: LoreStatus }
  | { readonly field: "beat_ref"; readonly value: string | null };

/** The project/Document/revision world a narrow command was issued against. */
export interface NarrowFieldCapture {
  readonly projectId: string;
  readonly documentId: string;
  /** Summary revision observed when the command was issued. */
  readonly revisionId: string;
}

/** The placement fields the volume-placement command owns exclusively (#481). */
export interface DocumentPlacement {
  readonly volumeId: string;
  readonly position: number;
  readonly updatedAt: string;
}

/**
 * Patch only the placement-owned summary fields — never title, word count,
 * or revision identity — and only while the captured revision still owns
 * the shell row (#469/#481): a response outrun by a newer save or
 * placement intent never overwrites newer authority.
 */
export function mergeProjectDocumentPlacement(
  project: Project,
  capture: NarrowFieldCapture,
  placement: DocumentPlacement,
): Project {
  if (project.id !== capture.projectId) return project;
  return {
    ...project,
    documents: project.documents.map((document) => {
      if (document.id !== capture.documentId) return document;
      if (document.current_revision_id !== capture.revisionId) return document;
      return {
        ...document,
        volume_id: placement.volumeId,
        position: placement.position,
        updated_at: placement.updatedAt,
      };
    }),
  };
}

/**
 * Remove exactly one deleted document's summary row (#481); every other
 * row, including a late duplicate removal, passes through unchanged.
 */
export function removeProjectDocument(project: Project, documentId: string): Project {
  if (!project.documents.some((document) => document.id === documentId)) return project;
  return {
    ...project,
    documents: project.documents.filter((document) => document.id !== documentId),
  };
}

/**
 * Patch exactly one narrow summary field, and only while the captured
 * project/Document identity still owns the shell row at the same revision
 * (task 3.4): an older-revision response never overwrites newer authority.
 */
export function mergeProjectNarrowField(
  project: Project,
  capture: NarrowFieldCapture,
  patch: NarrowSummaryPatch,
): Project {
  if (project.id !== capture.projectId) return project;
  const row = project.documents.find((document) => document.id === capture.documentId);
  if (row === undefined || row.current_revision_id !== capture.revisionId) return project;
  return {
    ...project,
    documents: project.documents.map((document) => {
      if (document.id !== capture.documentId) return document;
      return patch.field === "lore_status"
        ? { ...document, lore_status: patch.value }
        : { ...document, beat_ref: patch.value };
    }),
  };
}
