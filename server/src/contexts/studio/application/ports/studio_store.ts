import type { Principal } from "../../../../shared/application/ports/auth.js";

/** Persistence-neutral row shapes handed to the application layer. */
export interface ProjectRecord {
  id: string;
  ownerId: string | null;
  guestSessionId: string | null;
  title: string;
  description: string;
  settingsJson: string;
  importHash: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface DocumentRecord {
  id: string;
  projectId: string;
  kind: string;
  title: string;
  position: number;
  currentRevisionId: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface RevisionRecord {
  id: string;
  documentId: string;
  parentRevisionId: string | null;
  revisionNumber: number;
  contentMarkdown: string;
  metadataJson: string;
  source: string;
  createdAt: Date;
}

/** A document together with its current revision, the list/save/read shape. */
export interface DocumentWithCurrent extends DocumentRecord {
  currentRevision: RevisionRecord | null;
}

/** One full-text hit: the document id, its title, and a plain-text excerpt. */
export interface DocumentMatchRecord {
  documentId: string;
  title: string;
  excerpt: string;
}

/**
 * Principal scoping of every project query: owner data by owner id, guest
 * data by session id — exactly one of the two is set.
 */
export interface ProjectScope {
  ownerId: string | null;
  guestSessionId: string | null;
}

/** Derive the store scope from the authenticated principal. */
export function scopeForPrincipal(principal: Principal): ProjectScope {
  if (principal.kind === "owner" && principal.ownerId !== null) {
    return { ownerId: principal.ownerId, guestSessionId: null };
  }
  return { ownerId: null, guestSessionId: principal.sessionId };
}

export interface AddProjectInput {
  title: string;
  description: string;
  settingsJson: string;
  /** Seed document/revision written in the same transaction as the project. */
  seed: { kind: string; title: string; contentMarkdown: string; metadataJson: string } | null;
  now: Date;
}

export interface AddDocumentInput {
  kind: string;
  title: string;
  contentMarkdown: string;
  position: number;
  metadataJson: string;
  now: Date;
}

export interface AdvanceDocumentInput {
  contentMarkdown: string;
  baseRevisionId: string | null;
  title: string | null;
  metadataJson: string;
  source: string;
  now: Date;
}

/**
 * Persistence port of the authoring core. The application layer orchestrates
 * project, document, and revision behavior through this port; the Drizzle
 * store implements it transactionally in infrastructure.
 */
export interface StudioStore {
  addProject(
    scope: ProjectScope,
    input: AddProjectInput,
  ): {
    project: ProjectRecord;
    documents: DocumentWithCurrent[];
  };
  findProjects(scope: ProjectScope): ProjectRecord[];
  findProject(scope: ProjectScope, projectId: string): ProjectRecord;
  dropProject(scope: ProjectScope, projectId: string): void;

  findDocuments(scope: ProjectScope, projectId: string): DocumentWithCurrent[];
  findDocument(scope: ProjectScope, projectId: string, documentId: string): DocumentWithCurrent;
  addDocument(scope: ProjectScope, projectId: string, input: AddDocumentInput): DocumentWithCurrent;
  advanceDocument(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: AdvanceDocumentInput,
  ): DocumentWithCurrent;
  dropDocument(scope: ProjectScope, projectId: string, documentId: string): void;
  renumberDocuments(
    scope: ProjectScope,
    projectId: string,
    documentIds: string[],
    now: Date,
  ): DocumentWithCurrent[];
  nextPosition(scope: ProjectScope, projectId: string, kind: string): number;

  findRevisions(scope: ProjectScope, projectId: string, documentId: string): RevisionRecord[];
  findRevision(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    revisionId: string,
  ): RevisionRecord;

  /**
   * Run a pre-reduced MATCH expression against the project's FTS index.
   * The expression must come from `buildFtsMatchQuery`; the store never
   * reduces raw user input itself.
   */
  matchProjectDocuments(
    scope: ProjectScope,
    projectId: string,
    matchQuery: string,
  ): DocumentMatchRecord[];
}
