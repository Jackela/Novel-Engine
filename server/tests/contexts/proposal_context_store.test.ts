import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import type { ProposalContextSource } from "../../src/contexts/studio/application/ports/proposal_context_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ProposalContextStorePart } from "../../src/contexts/studio/infrastructure/proposal_context_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openConnection } from "../../src/shared/infrastructure/db/connection.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

function capturedEpoch(source: ProposalContextSource, ids: { outline: string; lore: string }) {
  const outline = source.documents.find((document) => document.id === ids.outline);
  const lore = source.documents.find((document) => document.id === ids.lore);
  if (outline === undefined || lore === undefined)
    throw new Error("Expected captured context rows.");
  return {
    targetBody: source.target.currentRevision?.contentMarkdown,
    beatRef: source.target.beatRef,
    outlineBody: outline.currentRevision?.contentMarkdown,
    loreBody: lore.currentRevision?.contentMarkdown,
    loreAliasesJson: lore.loreAliasesJson,
    loreStatus: lore.loreStatus,
    volumeOrder: source.volumes.map((volume) => volume.id),
    documentOrder: source.documents.map((document) => document.id),
  };
}

describe("proposal context store", () => {
  it("captures one WAL snapshot across a concurrent context commit", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-proposal-context-"));
    const databasePath = join(directory, "novel-engine.sqlite3");
    const studio = await openStudioDatabase(databasePath);
    const competing = openConnection(databasePath);
    try {
      const now = new Date("2026-09-03T01:00:00.000Z");
      const setupStore = new DrizzleStudioStore({ database: studio.db });
      const auth = new AuthService({
        store: new DrizzleAuthStore(studio.db),
        sessionSecret: "proposal-context-test-secret",
        now: () => now,
      });
      await auth.configureOwner("context-owner", "long-test-password");
      const principal = (await auth.createOwnerSession("context-owner", "long-test-password"))
        .principal;
      const scope = scopeForPrincipal(principal);
      const seeded = setupStore.addProject(scope, {
        title: "Coherent context",
        description: "",
        settingsJson: "{}",
        seed: {
          kind: "chapter",
          title: "Target",
          contentMarkdown: "Target A",
          metadataJson: "{}",
        },
        now,
      });
      const target = seeded.documents[0];
      const firstVolume = setupStore.findVolumes(scope, seeded.project.id)[0];
      if (target === undefined || firstVolume === undefined) {
        throw new Error("Expected seeded target and volume.");
      }
      const targetId = target.id;
      const targetRevisionId = target.currentRevisionId;
      const firstVolumeId = firstVolume.id;
      setupStore.setBeatReference(scope, seeded.project.id, targetId, {
        beatRef: "Beat A",
        now,
      });
      const secondVolume = setupStore.addVolume(scope, seeded.project.id, {
        title: "Second",
        now,
      });
      const sibling = setupStore.addDocument(scope, seeded.project.id, {
        kind: "chapter",
        title: "Sibling",
        contentMarkdown: "Sibling A",
        metadataJson: "{}",
        position: 1,
        volumeId: secondVolume.id,
        now,
      });
      const outline = setupStore.addDocument(scope, seeded.project.id, {
        kind: "outline",
        title: "Outline",
        contentMarkdown: "## Beat A\nOutline A",
        metadataJson: "{}",
        position: 1,
        volumeId: null,
        now,
      });
      const lore = setupStore.addDocument(scope, seeded.project.id, {
        kind: "character",
        title: "Lore",
        contentMarkdown: "Lore A",
        metadataJson: "{}",
        position: 1,
        volumeId: null,
        now,
      });
      setupStore.setLoreAliases(scope, seeded.project.id, lore.id, {
        aliases: ["alias-a"],
        now,
      });
      setupStore.setLoreStatus(scope, seeded.project.id, lore.id, { status: "stable", now });

      let committed = false;
      class InterleavingProposalContextStore extends ProposalContextStorePart {
        protected override afterScopedTargetRead(): void {
          if (committed) return;
          competing.raw.transaction(() => {
            const insertRevision = competing.raw.prepare(
              "INSERT INTO document_revisions " +
                "(id, document_id, parent_revision_id, revision_number, content_markdown, " +
                "metadata_json, source, created_at) VALUES (?, ?, ?, 2, ?, '{}', 'author', ?)",
            );
            insertRevision.run(
              "target-revision-b",
              targetId,
              targetRevisionId,
              "Target B",
              now.getTime() + 1,
            );
            insertRevision.run(
              "outline-revision-b",
              outline.id,
              outline.currentRevisionId,
              "## Beat B\nOutline B",
              now.getTime() + 1,
            );
            insertRevision.run(
              "lore-revision-b",
              lore.id,
              lore.currentRevisionId,
              "Lore B",
              now.getTime() + 1,
            );
            competing.raw
              .prepare("UPDATE documents SET current_revision_id = ?, beat_ref = ? WHERE id = ?")
              .run("target-revision-b", "Beat B", targetId);
            competing.raw
              .prepare("UPDATE documents SET current_revision_id = ? WHERE id = ?")
              .run("outline-revision-b", outline.id);
            competing.raw
              .prepare(
                "UPDATE documents SET current_revision_id = ?, lore_aliases_json = ?, " +
                  "lore_status = ? WHERE id = ?",
              )
              .run("lore-revision-b", '["alias-b"]', "deprecated", lore.id);
            competing.raw
              .prepare("UPDATE volumes SET position = 2 WHERE id = ?")
              .run(firstVolumeId);
            competing.raw
              .prepare("UPDATE volumes SET position = 1 WHERE id = ?")
              .run(secondVolume.id);
          })();
          committed = true;
        }
      }

      const store = new InterleavingProposalContextStore(studio.db);
      const capturedA = store.readProposalContext(scope, seeded.project.id, targetId);
      expect(capturedEpoch(capturedA, { outline: outline.id, lore: lore.id })).toEqual({
        targetBody: "Target A",
        beatRef: "Beat A",
        outlineBody: "## Beat A\nOutline A",
        loreBody: "Lore A",
        loreAliasesJson: '["alias-a"]',
        loreStatus: "stable",
        volumeOrder: [firstVolumeId, secondVolume.id],
        documentOrder: [targetId, sibling.id, lore.id, outline.id],
      });

      const capturedB = store.readProposalContext(scope, seeded.project.id, targetId);
      expect(capturedEpoch(capturedB, { outline: outline.id, lore: lore.id })).toEqual({
        targetBody: "Target B",
        beatRef: "Beat B",
        outlineBody: "## Beat B\nOutline B",
        loreBody: "Lore B",
        loreAliasesJson: '["alias-b"]',
        loreStatus: "deprecated",
        volumeOrder: [secondVolume.id, firstVolumeId],
        documentOrder: [sibling.id, targetId, lore.id, outline.id],
      });

      expect(
        setupStore.readProposalContext(scope, seeded.project.id, targetId).target.currentRevision
          ?.contentMarkdown,
      ).toBe("Target B");
      expect(() =>
        setupStore.readProposalContext({ ownerId: "foreign-owner" }, seeded.project.id, targetId),
      ).toThrow(NotFoundError);
      expect(() =>
        setupStore.readProposalContext(scope, seeded.project.id, "missing-document"),
      ).toThrow(
        `No document 'missing-document' exists in project '${seeded.project.id}': the id does not exist there, or the document belongs to a different project.`,
      );
    } finally {
      competing.raw.close();
      studio.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
