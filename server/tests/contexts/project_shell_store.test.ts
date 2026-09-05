import { randomUUID } from "node:crypto";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { RevisionSourceInvariantError } from "../../src/contexts/studio/domain/revision_source.js";
import {
  documentRevisions,
  documents,
  projects,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { owners } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const SUMMARY_KEYS = [
  "beatRef",
  "createdAt",
  "currentRevisionId",
  "id",
  "kind",
  "loreStatus",
  "position",
  "projectId",
  "revisionSource",
  "title",
  "updatedAt",
  "volumeId",
  "wordCount",
];

describe("project shell store seam", () => {
  it("separates structural summaries from one complete current Document", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-project-shell-"));
    const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
    try {
      const now = new Date("2026-09-03T00:00:00.000Z");
      const auth = new AuthService({
        store: new DrizzleAuthStore(studio.db),
        sessionSecret: "project-shell-store-secret",
        now: () => now,
      });
      await auth.configureOwner("shell-owner", "long-test-password");
      const principal = (await auth.createOwnerSession("shell-owner", "long-test-password"))
        .principal;
      const scope = scopeForPrincipal(principal);
      const store = new DrizzleStudioStore({ database: studio.db });
      const created = store.addProject(scope, {
        title: "Store shell",
        description: "",
        settingsJson: "{}",
        seed: {
          kind: "chapter",
          title: "Chapter 1",
          contentMarkdown: "one two 三四",
          metadataJson: '{"private":true}',
        },
        now,
      });
      const document = created.documents[0];
      if (document === undefined) throw new Error("expected seeded document");

      const shell = store.readProjectShell(scope, created.project.id);
      expect(shell.project.id).toBe(created.project.id);
      expect(shell.volumes).toHaveLength(1);
      expect(shell.documents).toHaveLength(1);
      expect(Object.keys(shell.documents[0] ?? {}).sort()).toEqual(SUMMARY_KEYS);
      expect(shell.documents[0]).toMatchObject({
        id: document.id,
        currentRevisionId: document.currentRevision?.id,
        revisionSource: "author",
        wordCount: 3,
      });

      const current = store.readCurrentDocument(scope, created.project.id, document.id);
      expect(current.currentRevision).toMatchObject({
        contentMarkdown: "one two 三四",
        metadataJson: '{"private":true}',
        source: "author",
        wordCount: 3,
      });

      const reordered = store.renumberDocuments(
        scope,
        created.project.id,
        [document.id],
        new Date(now.getTime() + 1),
      );
      expect(Object.keys(reordered[0] ?? {}).sort()).toEqual(SUMMARY_KEYS);
    } finally {
      studio.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("fails closed when a scoped document points at another owner's revision", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-project-shell-integrity-"));
    const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
    try {
      const now = new Date("2026-09-03T00:00:00.000Z");
      const auth = new AuthService({
        store: new DrizzleAuthStore(studio.db),
        sessionSecret: "project-shell-integrity-secret",
        now: () => now,
      });
      await auth.configureOwner("integrity-owner", "long-test-password");
      const principal = (await auth.createOwnerSession("integrity-owner", "long-test-password"))
        .principal;
      const scope = scopeForPrincipal(principal);
      const store = new DrizzleStudioStore({ database: studio.db });
      const created = store.addProject(scope, {
        title: "Scoped project",
        description: "",
        settingsJson: "{}",
        seed: {
          kind: "chapter",
          title: "Chapter 1",
          contentMarkdown: "owner body",
          metadataJson: "{}",
        },
        now,
      });
      const document = created.documents[0];
      if (document === undefined) throw new Error("expected seeded document");

      const foreignOwnerId = randomUUID();
      const foreignProjectId = randomUUID();
      const foreignDocumentId = randomUUID();
      const foreignRevisionId = randomUUID();
      studio.db
        .insert(owners)
        .values({
          id: foreignOwnerId,
          username: `foreign-${foreignOwnerId}`,
          password_hash: "not-a-login-credential",
          created_at: now,
        })
        .run();
      studio.db
        .insert(projects)
        .values({
          id: foreignProjectId,
          ownerId: foreignOwnerId,
          title: "Foreign project",
          description: "",
          settingsJson: "{}",
          createdAt: now,
          updatedAt: now,
        })
        .run();
      studio.db
        .insert(documents)
        .values({
          id: foreignDocumentId,
          projectId: foreignProjectId,
          kind: "note",
          title: "Foreign document",
          position: 1,
          currentRevisionId: foreignRevisionId,
          createdAt: now,
          updatedAt: now,
        })
        .run();
      studio.db
        .insert(documentRevisions)
        .values({
          id: foreignRevisionId,
          documentId: foreignDocumentId,
          revisionNumber: 1,
          contentMarkdown: "FOREIGN_BODY_SENTINEL",
          metadataJson: '{"foreign":true}',
          source: "import",
          wordCount: 987_654,
          createdAt: now,
        })
        .run();
      studio.db
        .update(documents)
        .set({ currentRevisionId: foreignRevisionId })
        .where(eq(documents.id, document.id))
        .run();

      expect(() => store.readProjectShell(scope, created.project.id)).toThrow(
        RevisionSourceInvariantError,
      );
      expect(() => store.readCurrentDocument(scope, created.project.id, document.id)).toThrow(
        "Document not found.",
      );
    } finally {
      studio.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
