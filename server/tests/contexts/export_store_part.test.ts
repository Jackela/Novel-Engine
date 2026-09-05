import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { and, eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { DocumentService } from "../../src/contexts/studio/application/document_service.js";
import { exportArtifactNames } from "../../src/contexts/studio/application/export_artifact_identity.js";
import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import type {
  ExportArtifactFormat,
  ExportSource,
  PreparedExportArtifact,
} from "../../src/contexts/studio/application/ports/export_store.js";
import { jobPageLimit } from "../../src/contexts/studio/application/ports/job_records.js";
import {
  type ProjectScope,
  scopeForPrincipal,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProjectService } from "../../src/contexts/studio/application/project_service.js";
import { projectSnapshots } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

interface DocumentPayload {
  id: string;
  current_revision_id: string;
}

interface ProjectPayload {
  id: string;
  documents: DocumentPayload[];
}

function monotonicClock(): () => Date {
  let milliseconds = Date.parse("2026-08-24T00:00:00.000Z");
  return () => {
    milliseconds += 1;
    return new Date(milliseconds);
  };
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-store-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const clock = monotonicClock();
  const store = new DrizzleStudioStore({ database: studio.db });
  const projects = new ProjectService(store, clock);
  const documents = new DocumentService(store, clock);
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "export-store-test-secret",
    now: clock,
  });
  await auth.configureOwner("exporter", "long-test-password");
  const principal = (await auth.createOwnerSession("exporter", "long-test-password")).principal;
  return {
    clock,
    studio,
    store,
    projects,
    documents,
    exportStore: new ExportStorePart(studio.db),
    scope: scopeForPrincipal(principal),
    principal,
  };
}

function newProject(
  projects: ProjectService,
  principal: Awaited<ReturnType<typeof openHarness>>["principal"],
  title: string,
): { projectId: string; chapter: DocumentPayload } {
  const project = projects.newProject(principal, { title }) as unknown as ProjectPayload;
  const chapter = project.documents[0];
  if (chapter === undefined) {
    throw new Error("Project creation must provide its seed chapter.");
  }
  return { projectId: project.id, chapter };
}

function capture(scope: ProjectScope, projectId: string, now: Date, store: ExportStorePart) {
  return store.readExportSource(scope, projectId, now);
}

function prepared(
  source: ExportSource,
  id: string,
  format: ExportArtifactFormat,
  createdAt: Date,
): PreparedExportArtifact {
  const { relativePath } = exportArtifactNames(source.projectId, id, format);
  return {
    source,
    id,
    format,
    relativePath,
    sizeBytes: id.length,
    checksumSha256: "a".repeat(64),
    createdAt,
  };
}

describe("ExportStorePart", () => {
  it("rejects a zero-chapter project before recording an export snapshot", async () => {
    const harness = await openHarness();
    try {
      const { projectId, chapter } = newProject(
        harness.projects,
        harness.principal,
        "Outline only",
      );
      harness.documents.removeDocument(harness.principal, projectId, chapter.id);
      harness.documents.newDocument(harness.principal, projectId, {
        kind: "outline",
        title: "Book map",
        contentMarkdown: "The outline has no exportable chapters.",
      });
      let artifactWrites = 0;
      const artifacts = new SnapshotArtifactService(harness.exportStore, {
        async writeSnapshotArtifact() {
          artifactWrites += 1;
          throw new Error("Zero-chapter export must not write an artifact.");
        },
        async readArtifactBytes() {
          throw new Error("Zero-chapter export must not read an artifact.");
        },
      });

      await expect(
        artifacts.recordCompletedExportJob(harness.principal, projectId, "markdown"),
      ).rejects.toThrow(InvalidOperationError);

      expect(artifactWrites).toBe(0);
      expect(harness.exportStore.listProjectArtifacts(harness.scope, projectId)).toEqual([]);
      expect(
        harness.studio.db
          .select()
          .from(projectSnapshots)
          .where(
            and(eq(projectSnapshots.projectId, projectId), eq(projectSnapshots.reason, "export")),
          )
          .all(),
      ).toEqual([]);
    } finally {
      harness.studio.close();
    }
  });

  it("rejects malformed artifact evidence without committing a database outcome", async () => {
    const harness = await openHarness();
    try {
      const { projectId } = newProject(
        harness.projects,
        harness.principal,
        "Invalid artifact evidence",
      );
      const source = capture(harness.scope, projectId, harness.clock(), harness.exportStore);
      const valid = prepared(source, "invalid-evidence", "markdown", harness.clock());
      const unsupportedFormat = { ...valid };
      Reflect.set(unsupportedFormat, "format", "pdf");
      const invalid: PreparedExportArtifact[] = [
        { ...valid, id: "../artifact" },
        { ...valid, relativePath: "outside.md" },
        { ...valid, sizeBytes: -1 },
        { ...valid, checksumSha256: "not-a-checksum" },
        unsupportedFormat,
      ];

      for (const input of invalid) {
        expect(() => harness.exportStore.recordCompletedExportJob(harness.scope, input)).toThrow();
        expect(harness.exportStore.listProjectArtifacts(harness.scope, projectId)).toEqual([]);
        expect(
          harness.store.collectProjectJobSummaries(harness.scope, projectId, {
            limit: jobPageLimit(50),
          }).jobs,
        ).toEqual([]);
      }
      expect(harness.studio.db.select().from(projectSnapshots).all()).toEqual([]);
    } finally {
      harness.studio.close();
    }
  });

  it("captures every document in stable order and ignores later review snapshots for reuse", async () => {
    const harness = await openHarness();
    try {
      const { projectId, chapter } = newProject(harness.projects, harness.principal, "Ashfall");
      const firstChapter = harness.documents.storeDocument(
        harness.principal,
        projectId,
        chapter.id,
        {
          baseRevisionId: chapter.current_revision_id,
          contentMarkdown: "First chapter.",
        },
      ) as unknown as DocumentPayload;
      const character = harness.documents.newDocument(harness.principal, projectId, {
        kind: "character",
        title: "Mara",
        contentMarkdown: "A non-chapter profile.",
      }) as unknown as DocumentPayload;
      const secondChapter = harness.documents.newDocument(harness.principal, projectId, {
        kind: "chapter",
        title: "Chapter 2",
        contentMarkdown: "Second chapter.",
      }) as unknown as DocumentPayload;

      const first = capture(harness.scope, projectId, harness.clock(), harness.exportStore);
      expect(first.documents.map((document) => document.documentId)).toContain(character.id);
      expect(
        first.documents
          .filter((document) => document.kind === "chapter")
          .map((document) => document.documentId),
      ).toEqual([firstChapter.id, secondChapter.id]);
      const firstArtifact = harness.exportStore.recordCompletedExportJob(
        harness.scope,
        prepared(first, "artifact-first", "markdown", harness.clock()),
      ).artifact;

      const source = harness.store.readReviewSource(harness.scope, projectId, harness.clock());
      harness.store.recordCompletedReviewJob(harness.scope, {
        source,
        provider: "mock",
        model: "deterministic-story-v1",
        summary: "review only",
        completedAt: harness.clock(),
        issues: [],
      });
      const second = capture(harness.scope, projectId, harness.clock(), harness.exportStore);

      expect(second.reuseSnapshotId).toBe(firstArtifact.snapshotId);
      expect(second.documents).toEqual(first.documents);
    } finally {
      harness.studio.close();
    }
  });

  it("creates fresh all-document snapshots after non-chapter changes without rewriting old data", async () => {
    const harness = await openHarness();
    try {
      const { projectId } = newProject(harness.projects, harness.principal, "Frozen outlines");
      const outline = harness.documents.newDocument(harness.principal, projectId, {
        kind: "outline",
        title: "Book map",
        contentMarkdown: "Original map.",
      }) as unknown as DocumentPayload;
      const first = capture(harness.scope, projectId, harness.clock(), harness.exportStore);
      const firstArtifact = harness.exportStore.recordCompletedExportJob(
        harness.scope,
        prepared(first, "artifact-original", "markdown", harness.clock()),
      ).artifact;

      const revisedOutline = harness.documents.storeDocument(
        harness.principal,
        projectId,
        outline.id,
        {
          baseRevisionId: outline.current_revision_id,
          contentMarkdown: "Revised map.",
        },
      ) as unknown as DocumentPayload;
      const second = capture(harness.scope, projectId, harness.clock(), harness.exportStore);
      const secondArtifact = harness.exportStore.recordCompletedExportJob(
        harness.scope,
        prepared(second, "artifact-revised", "docx", harness.clock()),
      ).artifact;
      const note = harness.documents.newDocument(harness.principal, projectId, {
        kind: "note",
        title: "Research",
        contentMarkdown: "New non-chapter.",
      }) as unknown as DocumentPayload;
      const third = capture(harness.scope, projectId, harness.clock(), harness.exportStore);
      const thirdArtifact = harness.exportStore.recordCompletedExportJob(
        harness.scope,
        prepared(third, "artifact-added", "epub", harness.clock()),
      ).artifact;

      expect(
        new Set([firstArtifact.snapshotId, secondArtifact.snapshotId, thirdArtifact.snapshotId])
          .size,
      ).toBe(3);
      expect(
        first.documents.find((document) => document.documentId === outline.id)?.contentMarkdown,
      ).toBe("Original map.");
      expect(second.documents.find((document) => document.documentId === outline.id)).toMatchObject(
        {
          revisionId: revisedOutline.current_revision_id,
          contentMarkdown: "Revised map.",
        },
      );
      expect(third.documents.map((document) => document.documentId)).toContain(note.id);
    } finally {
      harness.studio.close();
    }
  });
});
