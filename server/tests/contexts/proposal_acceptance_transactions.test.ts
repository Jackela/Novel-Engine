import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import {
  revisionPageLimit,
  scopeForPrincipal,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ProposalAcceptanceStorePart } from "../../src/contexts/studio/infrastructure/proposal_acceptance_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openConnection } from "../../src/shared/infrastructure/db/connection.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

function clock(): () => Date {
  let milliseconds = Date.parse("2026-08-31T00:00:00.000Z");
  return () => new Date(++milliseconds);
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-proposal-acceptance-"));
  directories.push(directory);
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const now = clock();
  const store = new DrizzleStudioStore({ database: database.db });
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "proposal-acceptance-test-secret",
    now,
  });
  await auth.configureOwner("acceptance-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("acceptance-owner", "long-test-password"))
    .principal;
  const scope = scopeForPrincipal(principal);
  const seeded = store.addProject(scope, {
    title: "Atomic acceptance",
    description: "",
    settingsJson: "{}",
    seed: { kind: "chapter", title: "Chapter 1", contentMarkdown: "old prose", metadataJson: "{}" },
    now: now(),
  });
  const document = seeded.documents[0];
  if (document?.currentRevision === null || document === undefined) {
    throw new Error("Expected a seeded document revision.");
  }
  const job = store.addJob(scope, {
    projectId: seeded.project.id,
    documentId: document.id,
    kind: "proposal",
    operation: "rewrite",
    status: "completed",
    provider: "mock",
    model: "deterministic-story-v1",
    requestJson: JSON.stringify({ base_revision_id: document.currentRevision.id }),
    resultJson: JSON.stringify({
      proposal_markdown: "new atomic prose",
      base_revision_id: document.currentRevision.id,
      accepted_revision_id: null,
    }),
    error: null,
    eventDetailsJson: "{}",
    now: now(),
  });
  return { database, document, job, now, scope, store, project: seeded.project };
}

describe("proposal acceptance transaction", () => {
  it("rolls the manuscript write back when the job binding fails", async () => {
    const harness = await openHarness();
    try {
      class ExplodingAcceptanceStore extends ProposalAcceptanceStorePart {
        protected override bindAcceptedRevision(): void {
          throw new Error("simulated job binding failure");
        }
      }
      const beforeProject = harness.store.findProject(harness.scope, harness.project.id);
      const exploding = new ExplodingAcceptanceStore(harness.database.db);

      expect(() =>
        exploding.acceptCompletedProposal(
          harness.scope,
          harness.project.id,
          harness.job.id,
          harness.now(),
        ),
      ).toThrow("simulated job binding failure");

      expect(
        harness.store.findRevisionSummaries(
          harness.scope,
          harness.project.id,
          harness.document.id,
          {
            limit: revisionPageLimit(100),
          },
        ).revisions,
      ).toHaveLength(1);
      expect(
        harness.store.findDocument(harness.scope, harness.project.id, harness.document.id)
          .currentRevisionId,
      ).toBe(harness.document.currentRevisionId);
      expect(harness.store.findProject(harness.scope, harness.project.id).updatedAt).toEqual(
        beforeProject.updatedAt,
      );
      expect(
        harness.store.matchProjectDocuments(harness.scope, harness.project.id, '"new"'),
      ).toEqual([]);
      expect(
        harness.store.matchProjectDocuments(harness.scope, harness.project.id, '"old"'),
      ).toHaveLength(1);
      expect(
        JSON.parse(
          harness.store.findJob(harness.scope, harness.project.id, harness.job.id).resultJson,
        ),
      ).toMatchObject({ accepted_revision_id: null });
    } finally {
      harness.database.close();
    }
  });

  it("takes the write lock before reading the idempotence decision", async () => {
    const harness = await openHarness();
    const competingConnection = openConnection(harness.database.databasePath);
    competingConnection.raw.pragma("busy_timeout = 1");
    try {
      let competingWriteWasBlocked = false;
      class LockObservingAcceptanceStore extends ProposalAcceptanceStorePart {
        protected override afterLockedJobRead(jobId: string): void {
          try {
            competingConnection.raw
              .prepare("UPDATE jobs SET updated_at = updated_at WHERE id = ?")
              .run(jobId);
          } catch (error) {
            competingWriteWasBlocked =
              error !== null &&
              typeof error === "object" &&
              (error as { code?: unknown }).code === "SQLITE_BUSY";
          }
        }
      }
      const accepted = new LockObservingAcceptanceStore(
        harness.database.db,
      ).acceptCompletedProposal(harness.scope, harness.project.id, harness.job.id, harness.now());

      expect(competingWriteWasBlocked).toBe(true);
      expect(JSON.parse(accepted.resultJson).accepted_revision_id).toEqual(expect.any(String));
    } finally {
      competingConnection.raw.close();
      harness.database.close();
    }
  });

  it("converges independent stores after serialization on one accepted revision", async () => {
    const harness = await openHarness();
    const secondConnection = openConnection(harness.database.databasePath);
    try {
      const firstStore = new ProposalAcceptanceStorePart(harness.database.db);
      const secondStore = new ProposalAcceptanceStorePart(secondConnection.db);
      const first = firstStore.acceptCompletedProposal(
        harness.scope,
        harness.project.id,
        harness.job.id,
        harness.now(),
      );
      const second = secondStore.acceptCompletedProposal(
        harness.scope,
        harness.project.id,
        harness.job.id,
        harness.now(),
      );

      expect(JSON.parse(second.resultJson).accepted_revision_id).toBe(
        JSON.parse(first.resultJson).accepted_revision_id,
      );
      expect(
        harness.store.findRevisionSummaries(
          harness.scope,
          harness.project.id,
          harness.document.id,
          {
            limit: revisionPageLimit(100),
          },
        ).revisions,
      ).toHaveLength(2);
    } finally {
      secondConnection.raw.close();
      harness.database.close();
    }
  });

  it("repairs a legacy split revision without creating another revision", async () => {
    const harness = await openHarness();
    try {
      const split = harness.store.advanceDocument(
        harness.scope,
        harness.project.id,
        harness.document.id,
        {
          contentMarkdown: "new atomic prose",
          baseRevisionId: harness.document.currentRevisionId,
          title: null,
          metadataJson: JSON.stringify({ ai_job_id: harness.job.id }),
          source: "ai-accepted",
          now: harness.now(),
        },
      );
      const repaired = new ProposalAcceptanceStorePart(harness.database.db).acceptCompletedProposal(
        harness.scope,
        harness.project.id,
        harness.job.id,
        harness.now(),
      );

      expect(JSON.parse(repaired.resultJson).accepted_revision_id).toBe(split.currentRevisionId);
      expect(
        harness.store.findRevisionSummaries(
          harness.scope,
          harness.project.id,
          harness.document.id,
          {
            limit: revisionPageLimit(100),
          },
        ).revisions,
      ).toHaveLength(2);
    } finally {
      harness.database.close();
    }
  });

  it("refuses to bind a mismatched legacy revision that only copies the job id", async () => {
    const harness = await openHarness();
    try {
      harness.store.advanceDocument(harness.scope, harness.project.id, harness.document.id, {
        contentMarkdown: "different prose",
        baseRevisionId: harness.document.currentRevisionId,
        title: null,
        metadataJson: JSON.stringify({ ai_job_id: harness.job.id }),
        source: "ai-accepted",
        now: harness.now(),
      });

      expect(() =>
        new ProposalAcceptanceStorePart(harness.database.db).acceptCompletedProposal(
          harness.scope,
          harness.project.id,
          harness.job.id,
          harness.now(),
        ),
      ).toThrow("Document changed since the requested base revision.");
      expect(
        JSON.parse(
          harness.store.findJob(harness.scope, harness.project.id, harness.job.id).resultJson,
        ).accepted_revision_id,
      ).toBeNull();
      expect(
        harness.store.findRevisionSummaries(
          harness.scope,
          harness.project.id,
          harness.document.id,
          {
            limit: revisionPageLimit(100),
          },
        ).revisions,
      ).toHaveLength(2);
    } finally {
      harness.database.close();
    }
  });
});
