import { describe, expect, it, vi } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ExportArtifactGateway } from "../../src/contexts/studio/application/export_artifact_service.js";
import type { ProjectArtifactCleaner } from "../../src/contexts/studio/application/ports/project_artifact_cleaner.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

function deferredTextProvider(): {
  factory: TextGenerationProviderFactory;
  started: Promise<void>;
  release: () => void;
} {
  let announce: (() => void) | undefined;
  let release: (() => void) | undefined;
  const started = new Promise<void>((resolve) => {
    announce = resolve;
  });
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  return {
    factory: (provider) => ({
      generateStructured: async (task) => {
        announce?.();
        await blocked;
        const content =
          task.step === "editorial_review"
            ? { findings: [] }
            : { chapter_markdown: validProposalProse };
        return {
          step: task.step,
          provider,
          model: "deferred-project-deletion-model",
          rawText: JSON.stringify(content),
          content,
          promptTokens: null,
          completionTokens: null,
        };
      },
    }),
    started,
    release: () => release?.(),
  };
}

function deferredArtifactGateway(): {
  gateway: ExportArtifactGateway;
  started: Promise<void>;
  release: () => void;
} {
  let announce: (() => void) | undefined;
  let release: (() => void) | undefined;
  const started = new Promise<void>((resolve) => {
    announce = resolve;
  });
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  return {
    gateway: {
      async writeSnapshotArtifact(request) {
        announce?.();
        await blocked;
        return {
          relativePath: `exports/${request.projectId}/${request.artifactId}.md`,
          sizeBytes: 1,
          checksumSha256: "a".repeat(64),
          acknowledge: async () => undefined,
          rollback: async () => undefined,
        };
      },
      async readArtifactBytes() {
        throw new Error("Unexpected artifact read.");
      },
    },
    started,
    release: () => release?.(),
  };
}

function deferredCleaner(): {
  cleaner: ProjectArtifactCleaner;
  started: Promise<void>;
  release: () => void;
} {
  let announce: (() => void) | undefined;
  let release: (() => void) | undefined;
  const started = new Promise<void>((resolve) => {
    announce = resolve;
  });
  const blocked = new Promise<void>((resolve) => {
    release = resolve;
  });
  return {
    cleaner: {
      async removeProjectArtifacts() {
        announce?.();
        await blocked;
      },
    },
    started,
    release: () => release?.(),
  };
}

describe("project-exclusive deletion", () => {
  it("rejects deletion while an export is in flight without partially deleting", async () => {
    const deferred = deferredArtifactGateway();
    const { app } = await buildStudioApp(undefined, {
      exportArtifactGateway: deferred.gateway,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Delete versus export");
      const pendingExport = call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "markdown",
      });
      await deferred.started;

      const rejected = await call(app, owner, "DELETE", `/api/projects/${project.id}`);
      expect(rejected.statusCode, rejected.body).toBe(409);
      expect(rejected.json().error).toMatchObject({
        code: "OPERATION_IN_FLIGHT",
        details: { project_id: project.id, operation: "export (markdown)" },
      });
      expect((await call(app, owner, "GET", `/api/projects/${project.id}`)).statusCode).toBe(200);

      deferred.release();
      expect((await pendingExport).statusCode).toBe(201);
      expect((await call(app, owner, "DELETE", `/api/projects/${project.id}`)).statusCode).toBe(
        204,
      );
    } finally {
      deferred.release();
      await app.close();
    }
  });

  it("rejects deletion while a review is in flight, then releases ownership", async () => {
    const deferred = deferredTextProvider();
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: deferred.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Delete versus review");
      const pendingReview = call(app, owner, "POST", `/api/projects/${project.id}/reviews`, {});
      await deferred.started;

      const rejected = await call(app, owner, "DELETE", `/api/projects/${project.id}`);
      expect(rejected.statusCode, rejected.body).toBe(409);
      expect(rejected.json().error).toMatchObject({
        code: "OPERATION_IN_FLIGHT",
        details: { project_id: project.id, document_id: null, operation: "review" },
      });
      expect((await call(app, owner, "GET", `/api/projects/${project.id}`)).statusCode).toBe(200);

      deferred.release();
      expect((await pendingReview).statusCode).toBe(201);
      expect((await call(app, owner, "DELETE", `/api/projects/${project.id}`)).statusCode).toBe(
        204,
      );
    } finally {
      deferred.release();
      await app.close();
    }
  });

  it("rejects deletion while a proposal is in flight, then releases ownership", async () => {
    const deferred = deferredTextProvider();
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: deferred.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Delete versus proposal");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Expected the seeded chapter.");
      const pendingProposal = call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue" },
      );
      await deferred.started;

      const rejected = await call(app, owner, "DELETE", `/api/projects/${project.id}`);
      expect(rejected.statusCode, rejected.body).toBe(409);
      expect(rejected.json().error).toMatchObject({
        code: "OPERATION_IN_FLIGHT",
        details: { project_id: project.id, document_id: document.id, operation: "continue" },
      });
      expect((await call(app, owner, "GET", `/api/projects/${project.id}`)).statusCode).toBe(200);

      deferred.release();
      expect((await pendingProposal).statusCode).toBe(200);
      expect((await call(app, owner, "DELETE", `/api/projects/${project.id}`)).statusCode).toBe(
        204,
      );
    } finally {
      deferred.release();
      await app.close();
    }
  });

  it("rejects a new export while committed deletion cleanup holds the project lock", async () => {
    const deferred = deferredCleaner();
    const { app } = await buildStudioApp(undefined, {
      projectArtifactCleaner: deferred.cleaner,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Delete owns project");
      const pendingDelete = call(app, owner, "DELETE", `/api/projects/${project.id}`);
      await deferred.started;

      const rejected = await call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "markdown",
      });
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

  it("keeps a committed deletion successful and reports cleanup failure once", async () => {
    const cleanupFailure = new Error("simulated project artifact cleanup failure");
    let calls = 0;
    const { app } = await buildStudioApp(undefined, {
      projectArtifactCleaner: {
        async removeProjectArtifacts() {
          calls += 1;
          throw cleanupFailure;
        },
      },
    });
    const logError = vi.spyOn(app.log, "error").mockImplementation(() => undefined);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Cleanup failure is secondary");

      const removed = await call(app, owner, "DELETE", `/api/projects/${project.id}`);

      expect(removed.statusCode, removed.body).toBe(204);
      expect(calls).toBe(1);
      expect((await call(app, owner, "GET", `/api/projects/${project.id}`)).statusCode).toBe(404);
      expect(
        logError.mock.calls.filter(
          ([details, message]) =>
            message === "project artifact cleanup failed" &&
            typeof details === "object" &&
            (details as Record<string, unknown>).project_artifact_cleanup_failed === true,
        ),
      ).toHaveLength(1);
    } finally {
      await app.close();
    }
  });
});
