import { eq } from "drizzle-orm";
import { describe, expect, it, vi } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { documents } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { jobEvents, jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

function failingProvider(): {
  readonly factory: TextGenerationProviderFactory;
  readonly factoryCalls: () => number;
} {
  let factoryCalls = 0;
  return {
    factory: () => {
      factoryCalls += 1;
      return {
        async generateStructured() {
          throw new TextGenerationProviderError("create retry source");
        },
      };
    },
    factoryCalls: () => factoryCalls,
  };
}

function evidence(app: Parameters<typeof studioDatabase>[0]) {
  const database = studioDatabase(app);
  return {
    jobs: database.select().from(jobs).all(),
    events: database.select().from(jobEvents).all(),
    usage: database.select().from(usageEvents).all(),
  };
}

async function retry(
  app: Parameters<typeof call>[0],
  owner: Parameters<typeof call>[1],
  projectId: string,
  sourceJobId: string,
  key: string,
) {
  return call(
    app,
    owner,
    "POST",
    `/api/projects/${projectId}/jobs/${sourceJobId}/retry`,
    undefined,
    { "idempotency-key": key },
  );
}

describe("proposal retry replay boundaries", () => {
  it("replays a terminal stale-base winner through the post-lookup claim branch", async () => {
    const provider = failingProvider();
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: provider.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Proposal retry claim race");
      const document = (await getProject(app, owner, project.id)).documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const baseA = document.current_revision_id;
      const source = (
        await call(
          app,
          owner,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue", instruction: "Keep claim evidence stable." },
        )
      ).json<JobPayload>();
      const advanced = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/${document.id}`,
        { content_markdown: "Revision B", base_revision_id: baseA },
      );
      expect(advanced.statusCode, advanced.body).toBe(200);

      const capture = vi.spyOn(DrizzleStudioStore.prototype, "readProposalContext");
      const claim = vi.spyOn(DrizzleStudioStore.prototype, "claimJobRetry");
      const key = "stale-base-claim-race-key-0001";
      const first = await retry(app, owner, project.id, source.id, key);
      expect(first.statusCode, first.body).toBe(200);
      const beforeReplay = evidence(app);

      // Model the lookup/claim interleave deterministically: the fast lookup
      // misses, while the claim transaction observes the terminal winner.
      vi.spyOn(DrizzleStudioStore.prototype, "findJobRetry").mockReturnValueOnce(null);
      const replay = await retry(app, owner, project.id, source.id, key);

      expect(replay.body).toBe(first.body);
      expect(claim).toHaveBeenCalledTimes(2);
      expect(claim.mock.results[1]?.value).toMatchObject({ created: false });
      expect(capture).toHaveBeenCalledTimes(1);
      expect(provider.factoryCalls()).toBe(1);
      expect(evidence(app)).toEqual(beforeReplay);
    } finally {
      vi.restoreAllMocks();
      await app.close();
    }
  });

  it("keeps the missing-current failure without fabricating stale-base evidence", async () => {
    const provider = failingProvider();
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: provider.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Proposal retry without current revision");
      const document = (await getProject(app, owner, project.id)).documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const baseA = document.current_revision_id;
      const source = (
        await call(
          app,
          owner,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue", instruction: "Keep missing-current evidence explicit." },
        )
      ).json<JobPayload>();
      studioDatabase(app)
        .update(documents)
        .set({ currentRevisionId: null })
        .where(eq(documents.id, document.id))
        .run();

      const capture = vi.spyOn(DrizzleStudioStore.prototype, "readProposalContext");
      const response = await retry(
        app,
        owner,
        project.id,
        source.id,
        "missing-current-retry-key-0001",
      );

      expect(response.statusCode, response.body).toBe(200);
      const failed = response.json<JobPayload>();
      expect(failed).toMatchObject({
        status: "failed",
        request: { base_revision_id: baseA },
        result: {},
        error: "Document has no current revision.",
      });
      expect(failed.events.at(-1)?.details).toEqual({
        error: "Document has no current revision.",
      });
      expect(JSON.stringify(failed)).not.toContain("base_revision_changed");
      expect(capture).toHaveBeenCalledTimes(1);
      expect(provider.factoryCalls()).toBe(1);
      expect(evidence(app).usage).toHaveLength(0);
    } finally {
      vi.restoreAllMocks();
      await app.close();
    }
  });
});
