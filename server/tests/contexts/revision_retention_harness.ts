import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type {
  AdvanceDocumentInput,
  DocumentWithCurrent,
} from "../../src/contexts/studio/application/ports/document_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  documentRevisions,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DocumentStorePart } from "../../src/contexts/studio/infrastructure/document_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import type { StudioDatabase } from "../../src/shared/infrastructure/db/startup.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

/**
 * Shared fixture for the DR-047 revision growth guards: a real SQLite
 * workspace with one owner, one project, and one seeded chapter revision.
 */
export const SEED_TIME = new Date("2025-01-01T00:00:00.000Z");

export interface RetentionHarness {
  cleanup: () => Promise<void>;
  currentRevisionId: string;
  documentId: string;
  projectId: string;
  scope: ReturnType<typeof scopeForPrincipal>;
  store: { projects: ProjectStorePart; documents: DocumentStorePart };
  studio: StudioDatabase;
}

export async function openRetentionHarness(): Promise<RetentionHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-revision-retention-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3")).catch(
    async (error: unknown) => {
      await rm(directory, { recursive: true, force: true });
      throw error;
    },
  );
  const cleanup = async (): Promise<void> => {
    try {
      studio.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  };
  try {
    const store = {
      projects: new ProjectStorePart(studio.db),
      documents: new DocumentStorePart(studio.db),
    };
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "revision-retention-test-secret",
      now: () => SEED_TIME,
    });
    await auth.configureOwner("retention-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("retention-owner", "long-test-password"))
      .principal;
    const scope = scopeForPrincipal(principal);
    const { project, documents } = store.projects.addProject(scope, {
      title: "Revision retention",
      description: "",
      settingsJson: "{}",
      seed: {
        kind: "chapter",
        title: "Chapter 1",
        contentMarkdown: "seed",
        metadataJson: "{}",
      },
      now: SEED_TIME,
    });
    const document = documents[0];
    if (document === undefined) throw new Error("Expected the seeded document.");
    const currentRevisionId = store.documents.findDocument(
      scope,
      project.id,
      document.id,
    ).currentRevisionId;
    if (currentRevisionId === null) throw new Error("Expected the seeded revision.");
    return {
      cleanup,
      currentRevisionId,
      documentId: document.id,
      projectId: project.id,
      scope,
      store,
      studio,
    };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

/** The revision id a save must have produced (null would mean no advance). */
export function requireRevisionId(value: string | null, message: string): string {
  if (value === null) throw new Error(message);
  return value;
}

/** The document's current revision id, asserted to exist. */
export function latestRevisionId(harness: RetentionHarness): string {
  return requireRevisionId(
    harness.store.documents.findDocument(harness.scope, harness.projectId, harness.documentId)
      .currentRevisionId,
    "Expected the document to have a current revision.",
  );
}

export interface SaveOptions {
  /** Milliseconds after `SEED_TIME`. */
  at: number;
  source?: AdvanceDocumentInput["source"];
  autosave?: boolean;
  metadataJson?: string;
  title?: string | null;
  contentMarkdown?: string;
}

/** Save against the document's current revision at `SEED_TIME + at`. */
export function save(
  harness: RetentionHarness,
  contentMarkdown: string,
  options: SaveOptions,
): DocumentWithCurrent {
  return harness.store.documents.advanceDocument(
    harness.scope,
    harness.projectId,
    harness.documentId,
    {
      contentMarkdown,
      baseRevisionId: latestRevisionId(harness),
      title: options.title === undefined ? "Chapter 1" : options.title,
      metadataJson: options.metadataJson ?? "{}",
      source: options.source ?? "author",
      autosave: options.autosave ?? true,
      now: new Date(SEED_TIME.getTime() + options.at),
    },
  );
}

/** The stored revision rows of the seeded document, oldest first. */
export function revisionRows(studio: StudioDatabase) {
  return studio.db
    .select({
      id: documentRevisions.id,
      revisionNumber: documentRevisions.revisionNumber,
      parentRevisionId: documentRevisions.parentRevisionId,
      contentMarkdown: documentRevisions.contentMarkdown,
      source: documentRevisions.source,
    })
    .from(documentRevisions)
    .orderBy(documentRevisions.revisionNumber)
    .all();
}

/** Pin one revision in an immutable snapshot, making it unfoldable. */
export function pinSnapshot(
  studio: StudioDatabase,
  input: { id: string; projectId: string; documentId: string; revisionId: string; createdAt: Date },
): void {
  studio.db
    .insert(projectSnapshots)
    .values({
      id: input.id,
      projectId: input.projectId,
      reason: "review",
      createdAt: input.createdAt,
    })
    .run();
  studio.db
    .insert(snapshotDocuments)
    .values({
      id: `${input.id}-document`,
      snapshotId: input.id,
      documentId: input.documentId,
      revisionId: input.revisionId,
      documentKind: "chapter",
      documentTitle: "Chapter 1",
      revisionMetadataJson: "{}",
      position: 0,
    })
    .run();
}
