import { describe, expect, it, vi } from "vitest";

import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import {
  jobEvents,
  jobs,
  usageEvents,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import { firstDocument, studioDatabase } from "./job_test_helpers.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  getDocument,
  type JobPayload,
  listRevisions,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const FAILURE_STATUSES = ["failed", "incomplete", "cancelled", "in_progress", "queued"];
const FAILURE_CANARY = "PROVIDER_RESPONSE_STATUS_PRIVATE_CANARY";

/** A real Responses adapter with only its outbound HTTP response controlled. */
function responsesFixture(status: string | undefined) {
  const transport = vi.fn<ProviderTransport>(async () =>
    Response.json({
      ...(status === undefined ? {} : { status }),
      error: status === "failed" ? { code: FAILURE_CANARY, message: FAILURE_CANARY } : null,
      incomplete_details: status === "incomplete" ? { reason: FAILURE_CANARY } : null,
      output: [
        {
          type: "message",
          status: "completed",
          content: [
            { type: "output_text", text: JSON.stringify({ chapter_markdown: validProposalProse }) },
          ],
        },
      ],
      usage: { input_tokens: 30, output_tokens: 40 },
    }),
  );
  return {
    transport,
    factory: () =>
      new DashScopeTextProvider({
        apiKey: fixtureApiKey("responses", "status-fixture"),
        transportMode: "responses",
        transport,
        retry: { maxAttempts: 3, delayMs: 0, sleep: async () => undefined },
      }),
  };
}

describe("synchronous Responses generation status", () => {
  it.each(FAILURE_STATUSES)("refuses %s despite parseable proposal text", async (status) => {
    const fixture = responsesFixture(status);
    const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Responses status failure");
      const document = firstDocument(project);
      const before = await getDocument(app, jar, project.id, document.id);
      const revisions = await listRevisions(app, jar, project.id, document.id);
      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", provider: "dashscope" },
      );
      expect(response.statusCode, response.body).toBe(200);
      const job = response.json<JobPayload>();
      expect(job).toMatchObject({
        status: "failed",
        error: `DashScope response generation did not complete (status: ${status}).`,
        result: { proposal_markdown: "", accepted_revision_id: null },
      });
      const accept = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/ai-proposals/${job.id}/accept`,
      );
      expect(accept.statusCode, accept.body).toBe(422);
      expect(await getDocument(app, jar, project.id, document.id)).toEqual(before);
      expect(await listRevisions(app, jar, project.id, document.id)).toEqual(revisions);
      expect(fixture.transport).toHaveBeenCalledTimes(1);
      const db = studioDatabase(app);
      expect(db.select().from(jobs).all()).toHaveLength(1);
      expect(db.select().from(jobEvents).all()).toHaveLength(1);
      const usage = db.select().from(usageEvents).all();
      expect(usage).toMatchObject([
        { outcome: "failed", token_source: "unreported", prompt_tokens: 0, completion_tokens: 0 },
      ]);
      expect(JSON.stringify([job, usage, db.select().from(jobEvents).all()])).not.toContain(
        FAILURE_CANARY,
      );
    } finally {
      await app.close();
    }
  });

  it.each(["completed", undefined, "future_status"])(
    "preserves successful extraction for status %s",
    async (status) => {
      const fixture = responsesFixture(status);
      const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
      try {
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Responses status compatibility");
        const document = firstDocument(project);
        const response = await call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue", provider: "dashscope" },
        );
        expect(response.statusCode, response.body).toBe(200);
        const job = response.json<JobPayload>();
        expect(job).toMatchObject({
          status: "completed",
          result: { proposal_markdown: validProposalProse },
        });
        const accept = await call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/ai-proposals/${job.id}/accept`,
        );
        expect(accept.statusCode, accept.body).toBe(200);
        expect(accept.json<JobPayload>().result.accepted_revision_id).toEqual(expect.any(String));
        expect((await getDocument(app, jar, project.id, document.id)).content_markdown).toBe(
          validProposalProse,
        );
        expect(fixture.transport).toHaveBeenCalledTimes(1);
      } finally {
        await app.close();
      }
    },
  );

  it("lands a failed keyed retry and replays it without another provider call", async () => {
    const fixture = responsesFixture("incomplete");
    const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Responses status retry");
      const document = firstDocument(project);
      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", provider: "dashscope" },
      );
      const source = response.json<JobPayload>();
      expect(source.status).toBe("failed");
      const retryPath = `/api/projects/${project.id}/jobs/${source.id}/retry`;
      const headers = { "idempotency-key": "responses-status-retry-0001" };
      const retried = await call(app, jar, "POST", retryPath, undefined, headers);
      expect(retried.statusCode, retried.body).toBe(200);
      const retry = retried.json<JobPayload>();
      expect(retry).toMatchObject({
        status: "failed",
        retry_of_job_id: source.id,
        error: source.error,
      });
      const replay = await call(app, jar, "POST", retryPath, undefined, headers);
      expect(replay.statusCode, replay.body).toBe(200);
      expect(replay.json<JobPayload>()).toEqual(retry);
      expect(fixture.transport).toHaveBeenCalledTimes(2);
      expect(await listRevisions(app, jar, project.id, document.id)).toHaveLength(1);
    } finally {
      await app.close();
    }
  });
});
