import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { describe, expect, it } from "vitest";

import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import * as databaseSchema from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

describe("single-document metadata writes", () => {
  it("reads back only the mutated document and its current revision", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-target-document-"));
    const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
    try {
      const now = new Date("2026-09-03T00:00:00.000Z");
      const setupStore = new DrizzleStudioStore({ database: studio.db });
      const auth = new AuthService({
        store: new DrizzleAuthStore(studio.db),
        sessionSecret: "target-document-test-secret",
        now: () => now,
      });
      await auth.configureOwner("target-owner", "long-test-password");
      const principal = (await auth.createOwnerSession("target-owner", "long-test-password"))
        .principal;
      const scope = scopeForPrincipal(principal);
      const seeded = setupStore.addProject(scope, {
        title: "Target reads",
        description: "",
        settingsJson: "{}",
        seed: {
          kind: "chapter",
          title: "Target chapter",
          contentMarkdown: "Target chapter body.",
          metadataJson: '{"target":true}',
        },
        now,
      });
      const chapter = seeded.documents[0];
      if (chapter === undefined) throw new Error("Expected the seeded chapter.");
      const lore = setupStore.addDocument(scope, seeded.project.id, {
        kind: "character",
        title: "Target lore",
        contentMarkdown: "Target lore body.",
        metadataJson: '{"role":"keeper"}',
        position: 1,
        volumeId: null,
        now,
      });
      setupStore.addDocument(scope, seeded.project.id, {
        kind: "world",
        title: "Large unrelated sibling",
        contentMarkdown: "s".repeat(1_000_000),
        metadataJson: "{}",
        position: 1,
        volumeId: null,
        now,
      });
      const targetVolume = setupStore.addVolume(scope, seeded.project.id, {
        title: "Target volume",
        now,
      });

      const executedSql: string[] = [];
      const tracedDatabase = drizzle(studio.raw, {
        schema: databaseSchema,
        logger: { logQuery: (query: string) => executedSql.push(query) },
      });
      const store = new DrizzleStudioStore({ database: tracedDatabase });

      function expectOneTargetRevisionRead<T>(operation: () => T): T {
        executedSql.length = 0;
        const result = operation();
        const revisionReads = executedSql.filter((query) =>
          query.includes('left join "document_revisions"'),
        );
        expect(revisionReads).toHaveLength(1);
        expect(revisionReads[0]).toContain('"documents"."id" = ?');
        expect(revisionReads[0]).toContain('"documents"."project_id" = ?');
        return result;
      }

      const beat = expectOneTargetRevisionRead(() =>
        store.setBeatReference(scope, seeded.project.id, chapter.id, {
          beatRef: "Opening",
          now,
        }),
      );
      expect(beat).toMatchObject({
        id: chapter.id,
        beatRef: "Opening",
        currentRevision: { contentMarkdown: "Target chapter body." },
      });

      const aliases = expectOneTargetRevisionRead(() =>
        store.setLoreAliases(scope, seeded.project.id, lore.id, { aliases: ["keeper"], now }),
      );
      expect(aliases).toMatchObject({
        id: lore.id,
        loreAliasesJson: '["keeper"]',
        currentRevision: { contentMarkdown: "Target lore body." },
      });

      const status = expectOneTargetRevisionRead(() =>
        store.setLoreStatus(scope, seeded.project.id, lore.id, { status: "stable", now }),
      );
      expect(status).toMatchObject({
        id: lore.id,
        loreStatus: "stable",
        currentRevision: { contentMarkdown: "Target lore body." },
      });

      const placed = expectOneTargetRevisionRead(() =>
        store.placeDocumentInVolume(scope, seeded.project.id, chapter.id, {
          volumeId: targetVolume.id,
          now,
        }),
      );
      expect(placed).toMatchObject({
        id: chapter.id,
        volumeId: targetVolume.id,
        currentRevision: { contentMarkdown: "Target chapter body." },
      });
    } finally {
      studio.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
