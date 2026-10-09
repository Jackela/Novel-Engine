import { describe, expect, it, vi } from "vitest";

import type {
  TextGenerationProviderFactory,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  getDocument,
  listRevisions,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const OUTCOMES = [
  {
    name: "failed",
    event: {
      type: "response.failed",
      response: {
        status: "failed",
        error: { code: "server_error", message: "generation failed" },
      },
    },
    diagnostic: "provider reported generation failed (code server_error)",
  },
  {
    name: "incomplete",
    event: {
      type: "response.incomplete",
      response: {
        status: "incomplete",
        incomplete_details: { reason: "max_output_tokens" },
      },
    },
    diagnostic:
      "provider reported response incomplete: max_output_tokens (code response.incomplete)",
  },
] as const;

const TASK: TextGenerationTask = {
  step: "chapter_draft",
  systemPrompt: "system",
  userPrompt: "write a chapter",
  responseSchema: { chapter_markdown: { type: "string" } },
  metadata: {},
};

/** Real Responses adapter with only its outbound HTTP boundary scripted. */
function responsesFixture(event: Record<string, unknown>, done = true) {
  const raw =
    [
      {
        type: "response.output_text.delta",
        delta: JSON.stringify({ chapter_markdown: validProposalProse }),
      },
      event,
    ]
      .map((frame) => `data: ${JSON.stringify(frame)}\n\n`)
      .join("") + (done ? "data: [DONE]\n\n" : "");
  const transport = vi.fn<ProviderTransport>(() =>
    Promise.resolve(new Response(raw, { headers: { "content-type": "text/event-stream" } })),
  );
  const provider = new DashScopeTextProvider({
    apiKey: fixtureApiKey("dashscope", "responses-failed-outcomes"),
    transportMode: "responses",
    transport,
    retry: { maxAttempts: 3, delayMs: 0, sleep: async () => undefined },
  });
  const factory: TextGenerationProviderFactory = (requested) => {
    if (requested !== "dashscope") throw new Error("Expected the Responses fixture provider.");
    return provider;
  };
  return { provider, factory, transport };
}

describe("Responses adverse outcomes remain failures (#674)", () => {
  it.each(OUTCOMES)(
    "rejects $name after prose without an outcome, with either DONE or EOF",
    async ({ event, diagnostic }) => {
      for (const done of [true, false]) {
        const fixture = responsesFixture(event, done);
        const onOutcome = vi.fn();
        const deltas: string[] = [];
        const consume = async () => {
          for await (const text of fixture.provider.generateStructuredStreaming(TASK, {
            onOutcome,
          }))
            deltas.push(text);
        };
        const failure = await consume().then(
          () => undefined,
          (error: unknown) => error,
        );
        expect(deltas).toEqual([validProposalProse]);
        expect(onOutcome).not.toHaveBeenCalled();
        expect(failure).toMatchObject({
          name: "ProviderTransportError",
          retryable: false,
          message: `DashScope generation failed for step 'chapter_draft': ${diagnostic}`,
        });
        expect(fixture.transport).toHaveBeenCalledTimes(1);
      }
    },
  );

  it.each(OUTCOMES)(
    "lands a failed Proposal Job for $name even when DONE follows",
    async ({ event, diagnostic }) => {
      const fixture = responsesFixture(event);
      const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
      try {
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Responses failure evidence");
        const summary = project.documents[0];
        if (summary === undefined) throw new Error("Expected a document.");
        const document = await getDocument(app, jar, project.id, summary.id);
        const revisions = await listRevisions(app, jar, project.id, summary.id);
        const response = await call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/documents/${summary.id}/ai-proposals/stream`,
          { operation: "continue", provider: "dashscope" },
        );
        expect(response.statusCode).toBe(200);
        const frames = response.body
          .split("\n\n")
          .filter(Boolean)
          .map((frame) => JSON.parse(frame.slice("data: ".length)) as ProposalStreamFrame);
        expect(frames.map((frame) => frame.type)).toEqual(["delta", "error"]);
        const terminal = frames.at(-1);
        if (terminal?.type !== "error") throw new Error("Expected a Provider failure.");
        expect(terminal.error.code).toBe("PROVIDER_FAILED");
        expect(terminal.error.message).toContain(diagnostic);

        const listing = await call(app, jar, "GET", `/api/projects/${project.id}/jobs`);
        expect(listing.statusCode).toBe(200);
        const jobs = listing.json<{ jobs: Array<{ id: string }> }>().jobs;
        expect(jobs).toHaveLength(1);
        const job = jobs[0];
        if (job === undefined) throw new Error("Expected the failed Job.");
        const detail = await call(app, jar, "GET", `/api/projects/${project.id}/jobs/${job.id}`);
        expect(detail.statusCode).toBe(200);
        expect(detail.json()).toMatchObject({
          status: "failed",
          error: terminal.error.message,
          result: {
            proposal_markdown: "",
            partial_markdown: validProposalProse,
            accepted_revision_id: null,
          },
        });
        expect(await getDocument(app, jar, project.id, summary.id)).toEqual(document);
        expect(await listRevisions(app, jar, project.id, summary.id)).toEqual(revisions);
        expect(fixture.transport).toHaveBeenCalledTimes(1);
      } finally {
        await app.close();
      }
    },
  );
});
