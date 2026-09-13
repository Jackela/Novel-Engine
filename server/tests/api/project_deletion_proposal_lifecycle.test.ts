import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProjectArtifactCleaner } from "../../src/contexts/studio/application/ports/project_artifact_cleaner.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, type CookieJar, call, ownerJar, seedProject } from "./studio_helpers.js";

function deferredCleaner(): {
  cleaner: ProjectArtifactCleaner;
  started: Promise<void>;
  release: () => void;
} {
  let announce: (() => void) | undefined;
  let release: (() => void) | undefined;
  return {
    cleaner: {
      async removeProjectArtifacts() {
        announce?.();
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      },
    },
    started: new Promise<void>((resolve) => {
      announce = resolve;
    }),
    release: () => release?.(),
  };
}

function disposalGatedProvider(): {
  factory: TextGenerationProviderFactory;
  disposing: Promise<void>;
  release: () => void;
} {
  let announce: (() => void) | undefined;
  let release: (() => void) | undefined;
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  return {
    factory: (provider) => ({
      async generateStructured(task) {
        return {
          step: task.step,
          provider,
          model: "disposal-gated-model",
          rawText: validProposalProse,
          content: { chapter_markdown: validProposalProse },
          promptTokens: null,
          completionTokens: null,
        };
      },
      async *generateStructuredStreaming(_task, options) {
        yield validProposalProse;
        options?.onOutcome?.({
          model: "disposal-gated-model",
          promptTokens: null,
          completionTokens: null,
        });
      },
      async dispose() {
        announce?.();
        await blocked;
      },
    }),
    disposing: new Promise<void>((resolve) => {
      announce = resolve;
    }),
    release: () => release?.(),
  };
}

async function expectDeletionConflict(
  app: Awaited<ReturnType<typeof buildStudioApp>>["app"],
  owner: CookieJar,
  projectId: string,
): Promise<void> {
  const rejected = await call(app, owner, "DELETE", `/api/projects/${projectId}`);
  expect(rejected.statusCode, rejected.body).toBe(409);
  expect(rejected.json().error).toMatchObject({
    code: "OPERATION_IN_FLIGHT",
    details: { project_id: projectId },
  });
  expect((await call(app, owner, "GET", `/api/projects/${projectId}`)).statusCode).toBe(200);
}

describe("project deletion and proposal lifecycle", () => {
  it("rejects new review and retry pipelines throughout committed deletion cleanup", async () => {
    const deferred = deferredCleaner();
    const { app } = await buildStudioApp(undefined, {
      projectArtifactCleaner: deferred.cleaner,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Delete before other pipelines");
      const pendingDelete = call(app, owner, "DELETE", `/api/projects/${project.id}`);
      await deferred.started;

      for (const target of [
        { path: `/api/projects/${project.id}/reviews`, payload: {} },
        { path: `/api/projects/${project.id}/jobs/missing/retry`, payload: undefined },
      ]) {
        const rejected = await call(
          app,
          owner,
          "POST",
          target.path,
          target.payload,
          target.path.endsWith("/retry")
            ? { "idempotency-key": "deleting-project-retry-0001" }
            : undefined,
        );
        expect(rejected.statusCode, rejected.body).toBe(409);
        expect(rejected.json().error).toMatchObject({
          code: "OPERATION_IN_FLIGHT",
          details: { project_id: project.id, operation: "project deletion" },
        });
      }

      deferred.release();
      expect((await pendingDelete).statusCode).toBe(204);
    } finally {
      deferred.release();
      await app.close();
    }
  });

  for (const endpoint of ["sync", "stream"] as const) {
    it(`rejects a new ${endpoint} proposal throughout committed deletion cleanup`, async () => {
      const deferred = deferredCleaner();
      const { app } = await buildStudioApp(undefined, {
        projectArtifactCleaner: deferred.cleaner,
      });
      try {
        const owner = await ownerJar(app);
        const project = await seedProject(app, owner, `Delete before ${endpoint} proposal`);
        const document = project.documents[0];
        if (document === undefined) throw new Error("Expected the seeded chapter.");
        const pendingDelete = call(app, owner, "DELETE", `/api/projects/${project.id}`);
        await deferred.started;

        const suffix = endpoint === "sync" ? "ai-proposals" : "ai-proposals/stream";
        const rejected = await call(
          app,
          owner,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/${suffix}`,
          { operation: "continue", provider: "mock" },
        );
        expect(rejected.statusCode, rejected.body).toBe(409);
        expect(rejected.json().error).toMatchObject({
          code: "OPERATION_IN_FLIGHT",
          details: { project_id: project.id, operation: "project deletion" },
        });

        deferred.release();
        expect((await pendingDelete).statusCode).toBe(204);
      } finally {
        deferred.release();
        await app.close();
      }
    });

    it(`blocks deletion until ${endpoint} proposal provider disposal finishes`, async () => {
      const deferred = disposalGatedProvider();
      const { app } = await buildStudioApp(undefined, {
        textProviderFactory: deferred.factory,
      });
      try {
        const owner = await ownerJar(app);
        const project = await seedProject(app, owner, `Dispose before ${endpoint} delete`);
        const document = project.documents[0];
        if (document === undefined) throw new Error("Expected the seeded chapter.");
        const suffix = endpoint === "sync" ? "ai-proposals" : "ai-proposals/stream";
        const pendingProposal = call(
          app,
          owner,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/${suffix}`,
          { operation: "continue", provider: "mock" },
        );
        await deferred.disposing;

        await expectDeletionConflict(app, owner, project.id);
        deferred.release();
        const completed = await pendingProposal;
        expect(completed.statusCode, completed.body).toBe(200);
        if (endpoint === "stream") expect(completed.body).toContain('"type":"done"');
        expect((await call(app, owner, "DELETE", `/api/projects/${project.id}`)).statusCode).toBe(
          204,
        );
      } finally {
        deferred.release();
        await app.close();
      }
    });
  }
});
