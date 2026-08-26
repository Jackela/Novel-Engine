import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { buildStudioApp, type CookieJar, call, ownerJar, seedProject } from "./studio_helpers.js";

/**
 * #305: identical synchronous pipeline submissions are deduplicated while
 * one is in flight. The provider factory is the controllable seam: each
 * generateStructured call signals that it started and then parks on a gate
 * the test controls, so the in-flight window is deterministic.
 */
function deferredProviderFactory(): {
  factory: TextGenerationProviderFactory;
  waitForStart: () => Promise<void>;
  resolveAll: () => void;
  failFirst: (error: Error) => void;
} {
  const gates: Array<{ resolve: () => void; reject: (error: Error) => void }> = [];
  let notifyStart: (() => void) | undefined;
  const factory: TextGenerationProviderFactory = (provider) => {
    const impl: TextGenerationProvider = {
      generateStructured: async (task) => {
        const startSignal = notifyStart;
        notifyStart = undefined;
        startSignal?.();
        await new Promise<void>((resolve, reject) => {
          gates.push({ resolve, reject });
        });
        return {
          step: task.step,
          provider,
          model: "deferred-model",
          rawText: validProposalProse,
          content: { chapter_markdown: validProposalProse },
          promptTokens: null,
          completionTokens: null,
        };
      },
    };
    return impl;
  };
  return {
    factory,
    waitForStart: () =>
      new Promise<void>((resolve) => {
        notifyStart = resolve;
      }),
    resolveAll: () => {
      const pending = [...gates];
      gates.length = 0;
      for (const gate of pending) {
        gate.resolve();
      }
    },
    failFirst: (error: Error) => {
      const gate = gates.shift();
      gate?.reject(error);
    },
  };
}

async function startDrafting(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
  operation: string,
) {
  const request = call(
    app,
    jar,
    "POST",
    `/api/projects/${projectId}/documents/${documentId}/ai-proposals`,
    { operation },
  );
  await Promise.resolve();
  await Promise.resolve();
  return request;
}

describe("in-flight operation deduplication (#305)", () => {
  it("rejects an identical concurrent proposal with 409 while one is running", async () => {
    const deferred = deferredProviderFactory();
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: deferred.factory,
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Dedup");
      const document = project.documents[0]!;
      const url = `/api/projects/${project.id}/documents/${document.id}/ai-proposals`;

      const first = startDrafting(app, jar, project.id, document.id, "continue");
      await deferred.waitForStart();
      const second = await call(app, jar, "POST", url, { operation: "continue" });

      expect(second.statusCode).toBe(409);
      expect(second.json()).toEqual({
        error: {
          code: "OPERATION_IN_FLIGHT",
          message: "The continue operation is already running for this document.",
          details: {
            project_id: project.id,
            document_id: document.id,
            operation: "continue",
          },
        },
      });

      deferred.resolveAll();
      const winner = await first;
      expect(winner.statusCode).toBe(200);
      expect(winner.json().kind).toBe("proposal");

      // The guard is released once the winner settles: a fresh request runs.
      const third = startDrafting(app, jar, project.id, document.id, "continue");
      await deferred.waitForStart();
      deferred.resolveAll();
      expect((await third).statusCode).toBe(200);
    } finally {
      await app.close();
    }
  });

  it("allows different operations on the same document to run concurrently", async () => {
    const deferred = deferredProviderFactory();
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: deferred.factory,
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Parallel ops");
      const document = project.documents[0]!;

      const rewrite = startDrafting(app, jar, project.id, document.id, "rewrite");
      await deferred.waitForStart();
      const generate = startDrafting(app, jar, project.id, document.id, "generate");
      await deferred.waitForStart();
      deferred.resolveAll();

      expect((await rewrite).statusCode).toBe(200);
      expect((await generate).statusCode).toBe(200);
    } finally {
      await app.close();
    }
  });

  it("releases the guard when the provider fails, so the next request runs", async () => {
    const deferred = deferredProviderFactory();
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: deferred.factory,
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Failed release");
      const document = project.documents[0]!;

      const first = startDrafting(app, jar, project.id, document.id, "continue");
      await deferred.waitForStart();
      deferred.failFirst(new TextGenerationProviderError("provider exploded"));
      const failed = await first;
      expect(failed.statusCode).toBe(200);
      expect(failed.json().status).toBe("failed");
      expect(failed.json().error).toContain("provider exploded");

      // The failed run released the guard: the same operation starts again.
      const second = startDrafting(app, jar, project.id, document.id, "continue");
      await deferred.waitForStart();
      deferred.resolveAll();
      expect((await second).statusCode).toBe(200);
    } finally {
      await app.close();
    }
  });

  it("answers 404, not 500, for a draft proposal on an unknown document", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Unknown doc");
      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/missing/ai-proposals`,
        { operation: "continue" },
      );
      expect(response.statusCode).toBe(404);
      expect(response.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });

  it("deduplicates identical concurrent exports while different formats run free", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Export dedup");
      const url = `/api/projects/${project.id}/exports`;

      // The artifact write is the async window: the second identical export
      // enters its handler while the first is still writing.
      const [first, second] = await Promise.all([
        call(app, jar, "POST", url, { format: "markdown" }),
        call(app, jar, "POST", url, { format: "markdown" }),
      ]);
      const statuses = [first.statusCode, second.statusCode].sort();
      expect(statuses).toEqual([201, 409]);
      const loser = first.statusCode === 409 ? first : second;
      expect(loser.json().error.code).toBe("OPERATION_IN_FLIGHT");
      expect(loser.json().error.details.operation).toBe("export (markdown)");

      // A different format of the same project never collides.
      const other = await call(app, jar, "POST", url, { format: "epub" });
      expect(other.statusCode).toBe(201);
    } finally {
      await app.close();
    }
  });
});
