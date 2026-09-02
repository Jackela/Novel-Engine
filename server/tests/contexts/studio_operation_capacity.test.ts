import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { createStudioServices } from "../../src/contexts/studio/application/studio_services.js";
import {
  OperationCapacityExceededError,
  OperationInFlightError,
} from "../../src/contexts/studio/domain/exceptions.js";
import {
  exports as exportArtifacts,
  projectSnapshots,
  reviews,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { jobEvents, jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";
import { validProposalProse } from "../api/proposal_test_helpers.js";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

function deferredFirstProvider(): {
  factory: TextGenerationProviderFactory;
  factoryCalls: () => number;
  generationStarted: Promise<void>;
  finishGeneration: () => void;
  disposalStarted: Promise<void>;
  finishDisposal: () => void;
} {
  let factoryCalls = 0;
  let announceGeneration: (() => void) | undefined;
  let resolveGeneration: (() => void) | undefined;
  let announceDisposal: (() => void) | undefined;
  let resolveDisposal: (() => void) | undefined;
  const generationStarted = new Promise<void>((resolve) => {
    announceGeneration = resolve;
  });
  const generationGate = new Promise<void>((resolve) => {
    resolveGeneration = resolve;
  });
  const disposalStarted = new Promise<void>((resolve) => {
    announceDisposal = resolve;
  });
  const disposalGate = new Promise<void>((resolve) => {
    resolveDisposal = resolve;
  });

  const factory: TextGenerationProviderFactory = (provider) => {
    const requestIndex = factoryCalls++;
    const implementation: TextGenerationProvider = {
      async generateStructured(task) {
        if (requestIndex === 0) {
          announceGeneration?.();
          await generationGate;
        }
        const content =
          task.step === "editorial_review"
            ? { findings: [] }
            : { chapter_markdown: validProposalProse };
        return {
          step: task.step,
          provider,
          model: "capacity-test-model",
          rawText: JSON.stringify(content),
          content,
          promptTokens: 1,
          completionTokens: 1,
        };
      },
      async *generateStructuredStreaming() {
        yield validProposalProse;
      },
      async dispose() {
        if (requestIndex !== 0) return;
        announceDisposal?.();
        await disposalGate;
      },
    };
    return implementation;
  };

  return {
    factory,
    factoryCalls: () => factoryCalls,
    generationStarted,
    finishGeneration: () => resolveGeneration?.(),
    disposalStarted,
    finishDisposal: () => resolveDisposal?.(),
  };
}

describe("Studio expensive-workflow capacity", () => {
  it("refuses every counted workflow before side effects and holds capacity through cleanup", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-operation-capacity-"));
    directories.push(directory);
    const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
    const store = new DrizzleStudioStore({ database: database.db });
    const provider = deferredFirstProvider();
    let artifactWrites = 0;
    let projectCleanups = 0;
    let milliseconds = Date.parse("2026-09-02T08:00:00.000Z");
    const now = (): Date => new Date(++milliseconds);
    const auth = new AuthService({
      store: new DrizzleAuthStore(database.db),
      sessionSecret: "operation-capacity-test-secret",
      now,
    });
    await auth.configureOwner("capacity-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("capacity-owner", "long-test-password"))
      .principal;
    const services = createStudioServices(store, {
      now,
      providerFactory: provider.factory,
      artifactStore: new ExportStorePart(database.db),
      artifactFiles: {
        async writeSnapshotArtifact(request) {
          artifactWrites += 1;
          return {
            relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
            sizeBytes: 1,
            checksumSha256: "a".repeat(64),
            acknowledge: async () => undefined,
            rollback: async () => undefined,
          };
        },
        async readArtifactBytes() {
          throw new Error("unexpected artifact read");
        },
      },
      projectArtifactCleaner: {
        async removeProjectArtifacts() {
          projectCleanups += 1;
        },
      },
      legacyWorkspaceReader: {
        read() {
          throw new Error("unexpected legacy read");
        },
        readConfinedLegacyWorkspace() {
          throw new Error("unexpected confined legacy read");
        },
      },
      operationCapacity: { applicationLimit: 1, projectLimit: 1 },
    });

    try {
      const firstProject = services.projects.newProject(principal, { title: "Active" }) as {
        id: string;
        documents: Array<{ id: string }>;
      };
      const secondProject = services.projects.newProject(principal, { title: "Refused" }) as {
        id: string;
        documents: Array<{ id: string }>;
      };
      const idleProject = services.projects.newProject(principal, { title: "Idle deletion" }) as {
        id: string;
      };
      const firstDocument = firstProject.documents[0];
      const secondDocument = secondProject.documents[0];
      if (firstDocument === undefined || secondDocument === undefined) {
        throw new Error("capacity fixture must seed both documents");
      }
      const scope = scopeForPrincipal(principal);
      const retryKinds = ["proposal", "review", "export"] as const;
      const retryJobs = retryKinds.map((kind) =>
        store.addJob(scope, {
          projectId: secondProject.id,
          documentId: kind === "proposal" ? secondDocument.id : null,
          kind,
          operation: kind === "proposal" ? "continue" : kind,
          status: "failed",
          provider: kind === "export" ? "studio" : "mock",
          model: "fixture-model",
          requestJson: kind === "export" ? '{"format":"markdown"}' : "{}",
          resultJson: "{}",
          error: "fixture failure",
          eventDetailsJson: '{"error":"fixture failure"}',
          now: now(),
        }),
      );
      const baseline = {
        jobs: database.db.select().from(jobs).all().length,
        events: database.db.select().from(jobEvents).all().length,
      };

      const active = services.proposals.draftProposal(
        principal,
        firstProject.id,
        firstDocument.id,
        { operation: "continue", instruction: "", provider: "mock" },
        () => undefined,
      );
      await provider.generationStarted;

      await expect(
        services.proposals.draftProposal(
          principal,
          firstProject.id,
          firstDocument.id,
          { operation: "continue", instruction: "", provider: "mock" },
          () => undefined,
        ),
      ).rejects.toBeInstanceOf(OperationInFlightError);
      await expect(
        services.proposals.draftProposal(
          principal,
          secondProject.id,
          secondDocument.id,
          { operation: "continue", instruction: "", provider: "mock" },
          () => undefined,
        ),
      ).rejects.toMatchObject({ scope: "application", inFlight: 1 });

      const refusedSession = services.proposals.draftProposalStream(
        principal,
        secondProject.id,
        secondDocument.id,
        { operation: "continue", instruction: "", provider: "mock" },
        () => undefined,
      );
      try {
        await expect(refusedSession.frames.next()).rejects.toBeInstanceOf(
          OperationCapacityExceededError,
        );
      } finally {
        refusedSession.releaseCapacity();
      }
      await expect(
        services.jobHistory.recordReviewJob(principal, secondProject.id),
      ).rejects.toBeInstanceOf(OperationCapacityExceededError);
      await expect(
        services.jobHistory.recordExportJob(principal, secondProject.id, "markdown"),
      ).rejects.toBeInstanceOf(OperationCapacityExceededError);
      for (const retry of retryJobs) {
        await expect(
          services.jobHistory.reexecuteProjectJob(
            principal,
            secondProject.id,
            retry.id,
            () => undefined,
          ),
        ).rejects.toBeInstanceOf(OperationCapacityExceededError);
      }

      expect(provider.factoryCalls()).toBe(1);
      expect(artifactWrites).toBe(0);
      expect(database.db.select().from(jobs).all()).toHaveLength(baseline.jobs);
      expect(database.db.select().from(jobEvents).all()).toHaveLength(baseline.events);
      expect(database.db.select().from(usageEvents).all()).toHaveLength(0);
      expect(database.db.select().from(projectSnapshots).all()).toHaveLength(0);
      expect(database.db.select().from(reviews).all()).toHaveLength(0);
      expect(database.db.select().from(exportArtifacts).all()).toHaveLength(0);

      await expect(
        services.projects.removeProject(principal, idleProject.id),
      ).resolves.toBeUndefined();
      expect(projectCleanups).toBe(1);

      provider.finishGeneration();
      await provider.disposalStarted;
      expect(database.db.select().from(jobs).all()).toHaveLength(baseline.jobs + 1);
      await expect(
        services.jobHistory.recordReviewJob(principal, secondProject.id),
      ).rejects.toBeInstanceOf(OperationCapacityExceededError);

      provider.finishDisposal();
      await expect(active).resolves.toMatchObject({ status: "completed" });
      await expect(
        services.jobHistory.recordReviewJob(principal, secondProject.id),
      ).resolves.toMatchObject({
        kind: "review",
        status: "completed",
      });
      expect(provider.factoryCalls()).toBe(2);
    } finally {
      database.close();
    }
  });
});
