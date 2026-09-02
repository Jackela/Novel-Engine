import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
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
});
