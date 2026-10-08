import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { jobs, usageEvents } from "../../src/contexts/studio/infrastructure/db/schema.js";
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

type ProviderName = "dashscope" | "openai_compatible";

const PROVIDERS = [
  { provider: "dashscope", label: "DashScope" },
  { provider: "openai_compatible", label: "OpenAI-compatible" },
] as const;
const RAW_PROSE = `  ${validProposalProse}\n\n`;

/** Complete wrapper and usage frames, with an optional upstream terminal marker. */
function providerStreamFactory(
  provider: ProviderName,
  terminal: boolean,
): { factory: TextGenerationProviderFactory; calls: () => number } {
  let calls = 0;
  const content = JSON.stringify({ chapter_markdown: RAW_PROSE });
  const events =
    provider === "dashscope"
      ? [
          { output: { choices: [{ message: { content } }] } },
          { usage: { input_tokens: 21, output_tokens: 34 } },
        ]
      : [
          { choices: [{ delta: { content } }] },
          { choices: [], usage: { prompt_tokens: 21, completion_tokens: 34 } },
        ];
  const body =
    events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("") +
    (terminal ? "data: [DONE]\n\n" : "");
  const transport = async () => {
    calls += 1;
    return new Response(body, {
      status: 200,
      headers: { "content-type": "text/event-stream" },
    });
  };
  const apiKey = fixtureApiKey(provider, "stream-completion");
  const retry = { maxAttempts: 3, delayMs: 0, sleep: async () => {} };
  const factory: TextGenerationProviderFactory = (requested) => {
    if (requested !== provider) throw new Error("Unexpected stream fixture provider.");
    return provider === "dashscope"
      ? new DashScopeTextProvider({ apiKey, retry, transport })
      : new OpenAICompatibleTextProvider({ apiKey, retry, transport });
  };
  return { factory, calls: () => calls };
}

/** Parse the endpoint's buffered SSE response without discarding terminal frames. */
function parseFrames(raw: string): ProposalStreamFrame[] {
  expect(raw.endsWith("\n\n")).toBe(true);
  return raw
    .split("\n\n")
    .filter((part) => part !== "")
    .map((part) => {
      expect(part.startsWith("data: ")).toBe(true);
      return JSON.parse(part.slice("data: ".length)) as ProposalStreamFrame;
    });
}

describe("proposal stream upstream completion (#674)", () => {
  it.each(PROVIDERS)(
    "fails $provider EOF after complete prose and usage without accepting the proposal",
    async ({ provider, label }) => {
      const fixture = providerStreamFactory(provider, false);
      const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
      try {
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Truncated upstream stream");
        const summary = project.documents[0];
        if (summary === undefined) throw new Error("Expected a default document.");
        const document = await getDocument(app, jar, project.id, summary.id);
        const revisions = await listRevisions(app, jar, project.id, document.id);

        const response = await call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals/stream`,
          { operation: "continue", provider },
        );
        expect(response.statusCode, response.body).toBe(200);
        const frames = parseFrames(response.body);
        const deltas = frames.filter(
          (frame): frame is Extract<ProposalStreamFrame, { type: "delta" }> =>
            frame.type === "delta",
        );
        expect(deltas.length).toBeGreaterThan(0);
        expect(deltas.map((frame) => frame.text).join("")).toBe(RAW_PROSE);
        expect(frames.filter((frame) => frame.type === "done")).toHaveLength(0);
        expect(frames.filter((frame) => frame.type === "error")).toHaveLength(1);
        const terminal = frames.at(-1);
        if (terminal === undefined || terminal.type !== "error") {
          throw new Error(`Expected a terminal error frame: ${response.body}`);
        }
        expect(terminal.error.code).toBe("PROVIDER_FAILED");
        expect(terminal.error.message).toContain(
          `${label} generation failed for step 'chapter_revision': stream ended without a terminal frame`,
        );

        const database = app.studioDb?.db;
        if (database === undefined) throw new Error("Expected the studio database.");
        const persisted = database.select().from(jobs).all();
        expect(persisted).toHaveLength(1);
        const job = persisted[0];
        if (job === undefined) throw new Error("Expected the failed proposal job.");
        expect(job).toMatchObject({ status: "failed", error: terminal.error.message, provider });
        expect(JSON.parse(job.result_json)).toEqual({
          proposal_markdown: "",
          partial_markdown: validProposalProse,
          base_revision_id: document.current_revision_id,
          accepted_revision_id: null,
        });
        const usage = database.select().from(usageEvents).all();
        expect(usage).toHaveLength(1);
        expect(usage[0]).toMatchObject({
          job_id: job.id,
          provider,
          outcome: "failed",
          token_source: "unreported",
          prompt_tokens: 0,
          completion_tokens: 0,
        });
        expect(fixture.calls()).toBe(1);
        expect(await getDocument(app, jar, project.id, document.id)).toEqual(document);
        expect(await listRevisions(app, jar, project.id, document.id)).toEqual(revisions);
      } finally {
        await app.close();
      }
    },
  );

  it.each(PROVIDERS)(
    "completes $provider with the same prose and usage when DONE is present",
    async ({ provider }) => {
      const fixture = providerStreamFactory(provider, true);
      const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
      try {
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Completed upstream stream");
        const document = project.documents[0];
        if (document === undefined) throw new Error("Expected a default document.");
        const response = await call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals/stream`,
          { operation: "continue", provider },
        );
        expect(response.statusCode, response.body).toBe(200);
        const frames = parseFrames(response.body);
        expect(frames.map((frame) => frame.type)).toEqual(["delta", "done"]);
        const done = frames.at(-1);
        if (done === undefined || done.type !== "done") throw new Error("Expected done frame.");
        expect(done.job).toMatchObject({
          status: "completed",
          result: { proposal_markdown: validProposalProse, accepted_revision_id: null },
        });
        const database = app.studioDb?.db;
        if (database === undefined) throw new Error("Expected the studio database.");
        expect(database.select().from(jobs).all()).toHaveLength(1);
        const usage = database.select().from(usageEvents).all();
        expect(usage).toHaveLength(1);
        expect(usage[0]).toMatchObject({
          job_id: done.job.id,
          outcome: "completed",
          token_source: "provider",
          prompt_tokens: 21,
          completion_tokens: 34,
        });
        expect(fixture.calls()).toBe(1);
      } finally {
        await app.close();
      }
    },
  );
});
