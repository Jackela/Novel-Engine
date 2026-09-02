import { describe, expect, it, vi } from "vitest";
import type {
  TextGenerationProviderFactory,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { jobEvents, jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  type JobPayload,
  listRevisions,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const STALE_ERROR = "Proposal retry base revision is no longer current.";

function retryProvider(): {
  readonly factory: TextGenerationProviderFactory;
  readonly factoryCalls: () => number;
  readonly tasks: readonly TextGenerationTask[];
} {
  let factoryCalls = 0;
  const tasks: TextGenerationTask[] = [];
  return {
    factory: (provider) => {
      factoryCalls += 1;
      return {
        async generateStructured(task) {
          tasks.push(task);
          if (tasks.length === 1) throw new TextGenerationProviderError("create retry source");
          return {
            step: task.step,
            provider,
            model: "retry-base-model",
            rawText: validProposalProse,
            content: { chapter_markdown: validProposalProse },
            promptTokens: 7,
            completionTokens: 11,
          };
        },
      };
    },
    factoryCalls: () => factoryCalls,
    tasks,
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

describe("proposal retry base revision fidelity", () => {
  it("lands closed A/B evidence and replays it without rebasing or repeated work", async () => {
    const provider = retryProvider();
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: provider.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Immutable proposal retry base");
      const current = await getProject(app, owner, project.id);
      const document = current.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const baseA = document.current_revision_id;

      const original = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", instruction: "Preserve the original base." },
      );
      const source = original.json<JobPayload>();
      expect(source).toMatchObject({ status: "failed", request: { base_revision_id: baseA } });

      const advanced = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/${document.id}`,
        { content_markdown: "Revision B", base_revision_id: baseA },
      );
      expect(advanced.statusCode, advanced.body).toBe(200);
      const currentB = advanced.json().current_revision_id as string;
      expect(currentB).not.toBe(baseA);

      const capture = vi.spyOn(DrizzleStudioStore.prototype, "readProposalContext");
      const first = await retry(app, owner, project.id, source.id, "stale-base-retry-key-0001");
      expect(first.statusCode, first.body).toBe(200);
      const stale = first.json<JobPayload>();
      expect(stale).toMatchObject({
        status: "failed",
        model: source.model,
        request: { base_revision_id: baseA },
        result: {
          proposal_markdown: "",
          base_revision_id: baseA,
          accepted_revision_id: null,
        },
        error: STALE_ERROR,
        retry_of_job_id: source.id,
      });
      expect(stale.result).toEqual({
        proposal_markdown: "",
        base_revision_id: baseA,
        accepted_revision_id: null,
      });
      expect(stale.events.map((event) => event.status)).toEqual(["running", "failed"]);
      expect(stale.events[1]?.details).toEqual({
        error: STALE_ERROR,
        reason: "base_revision_changed",
        base_revision_id: baseA,
        current_revision_id: currentB,
      });
      expect(capture).toHaveBeenCalledTimes(1);
      expect(provider.factoryCalls()).toBe(1);
      expect(provider.tasks).toHaveLength(1);
      expect(evidence(app)).toMatchObject({ jobs: [{}, {}], events: [{}, {}, {}], usage: [] });
      expect(await listRevisions(app, owner, project.id, document.id)).toHaveLength(2);

      const beforeReplay = evidence(app);
      const replay = await retry(app, owner, project.id, source.id, "stale-base-retry-key-0001");
      expect(replay.body).toBe(first.body);
      expect(capture).toHaveBeenCalledTimes(1);
      expect(evidence(app)).toEqual(beforeReplay);

      const distinct = await retry(app, owner, project.id, source.id, "stale-base-retry-key-0002");
      expect(distinct.json<JobPayload>()).toMatchObject({
        status: "failed",
        request: { base_revision_id: baseA },
        error: STALE_ERROR,
      });
      expect(capture).toHaveBeenCalledTimes(2);

      const chained = await retry(app, owner, project.id, stale.id, "stale-base-chain-key-0001");
      expect(chained.json<JobPayload>()).toMatchObject({
        status: "failed",
        request: { base_revision_id: baseA },
        result: { base_revision_id: baseA },
        error: STALE_ERROR,
        retry_of_job_id: stale.id,
      });
      expect(capture).toHaveBeenCalledTimes(3);
      expect(provider.factoryCalls()).toBe(1);
      expect(evidence(app)).toMatchObject({
        jobs: [{}, {}, {}, {}],
        events: [{}, {}, {}, {}, {}, {}, {}],
        usage: [],
      });
    } finally {
      vi.restoreAllMocks();
      await app.close();
    }
  });

  it("uses unchanged base A for the task, result, and usage evidence", async () => {
    const provider = retryProvider();
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: provider.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Current proposal retry base");
      const current = await getProject(app, owner, project.id);
      const document = current.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const baseA = document.current_revision_id;
      const original = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", instruction: "Retry from A." },
      );
      const source = original.json<JobPayload>();

      const response = await retry(
        app,
        owner,
        project.id,
        source.id,
        "current-base-retry-key-0001",
      );
      expect(response.statusCode, response.body).toBe(200);
      expect(response.json<JobPayload>()).toMatchObject({
        status: "completed",
        request: { base_revision_id: baseA },
        result: { base_revision_id: baseA, accepted_revision_id: null },
      });
      expect(provider.tasks[1]?.metadata.base_revision_id).toBe(baseA);
      const usage = evidence(app).usage;
      expect(usage).toHaveLength(1);
      expect(JSON.parse(usage[0]?.request_evidence_json ?? "{}")).toEqual({
        operation: "continue",
        base_revision_id: baseA,
      });
    } finally {
      await app.close();
    }
  });
});
