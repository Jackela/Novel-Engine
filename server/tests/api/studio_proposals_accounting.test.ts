import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import { wordCount } from "../../src/contexts/studio/application/payloads.js";
import { jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import { capturingFactory, propose, validProposalProse } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  getProject,
  guestJar,
  listRevisions,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

type ProviderName = "dashscope" | "openai_compatible";

function malformedStructuredFactory(
  provider: ProviderName,
  chapterMarkdown: null | number,
): TextGenerationProviderFactory {
  const rawText = JSON.stringify({ chapter_markdown: chapterMarkdown });
  const transport = async () =>
    new Response(
      JSON.stringify(
        provider === "dashscope"
          ? { output: { choices: [{ message: { content: rawText } }] } }
          : { choices: [{ message: { content: rawText } }] },
      ),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  const retry = { maxAttempts: 1, delayMs: 0, sleep: async () => {} };
  return () =>
    provider === "dashscope"
      ? new DashScopeTextProvider({ apiKey: fixtureApiKey("dashscope", "test"), retry, transport })
      : new OpenAICompatibleTextProvider({
          apiKey: fixtureApiKey("openai", "test"),
          retry,
          transport,
        });
}

function transportRejectionFactory(
  provider: ProviderName,
  apiKey: string,
  prefix: string,
): TextGenerationProviderFactory {
  const transport = async () => {
    throw new TypeError(`${prefix}:${apiKey}:${prefix}`);
  };
  const retry = { maxAttempts: 1, delayMs: 0, sleep: async () => {} };
  return (requested) => {
    if (requested !== provider) {
      throw new Error("Transport rejection fixture received an unexpected provider.");
    }
    return provider === "dashscope"
      ? new DashScopeTextProvider({ apiKey, retry, transport })
      : new OpenAICompatibleTextProvider({ apiKey, retry, transport });
  };
}

const malformedStructuredCases = [
  { provider: "dashscope", chapterMarkdown: null, providerRawText: '{"chapter_markdown":""}' },
  {
    provider: "openai_compatible",
    chapterMarkdown: 42,
    providerRawText: '{"chapter_markdown":"42"}',
  },
] as const;

const transportRejectionCases = [
  {
    provider: "dashscope",
    apiKey: fixtureApiKey("dashscope-transport-credential", "that-must-not-leak"),
    prefix: "dashscope-transport-prefix-that-must-not-leak",
    error: "DashScope generation failed for step 'chapter_revision': transport request failed.",
  },
  {
    provider: "openai_compatible",
    apiKey: fixtureApiKey("openai-transport-credential", "that-must-not-leak"),
    prefix: "openai-transport-prefix-that-must-not-leak",
    error:
      "OpenAI-compatible generation failed for step 'chapter_revision': transport request failed.",
  },
] as const;

describe("proposal accounting and scoping", () => {
  it("records usage with the word-count fallback", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Usage");
      const document = project.documents[0]!;
      const instruction = "Tighten the chase through the archive."; // 6 words by the shared counter

      const response = await propose(app, jar, project.id, document.id, {
        operation: "continue",
        instruction,
      });
      const job = response.json();
      const documentPayload = (await getProject(app, jar, project.id)).documents[0]!;
      const usage = app.studioDb!.db.select().from(usageEvents).all();
      expect(usage).toHaveLength(1);
      expect(usage[0]!.job_id).toBe(job.id);
      expect(usage[0]!.provider).toBe("mock");
      expect(usage[0]!.model).toBe("deterministic-story-v1");
      expect(usage[0]!.prompt_tokens).toBe(wordCount(instruction));
      expect(usage[0]!.completion_tokens).toBe(wordCount(job.result.proposal_markdown));
      expect(JSON.parse(usage[0]!.request_evidence_json)).toEqual({
        operation: "continue",
        base_revision_id: documentPayload.current_revision_id,
      });
    } finally {
      await app.close();
    }
  });

  it("prefers provider-reported token counts over the fallback", async () => {
    const capture = capturingFactory({
      markdown: validProposalProse,
      promptTokens: 11,
      completionTokens: 13,
    });
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Counted");
      const document = project.documents[0]!;
      await propose(app, jar, project.id, document.id, { operation: "generate" });

      const usage = app.studioDb!.db.select().from(usageEvents).all();
      expect(usage).toHaveLength(1);
      expect(usage[0]!.prompt_tokens).toBe(11);
      expect(usage[0]!.completion_tokens).toBe(13);
      expect(usage[0]!.model).toBe("captured-model");
    } finally {
      await app.close();
    }
  });

  it.each(malformedStructuredCases)(
    "fails $provider malformed chapter content without persisting accounting",
    async ({ provider, chapterMarkdown, providerRawText }) => {
      const { app } = await buildStudioApp(undefined, {
        textProviderFactory: malformedStructuredFactory(provider, chapterMarkdown),
      });
      try {
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Malformed provider output");
        const document = project.documents[0];
        if (document === undefined) {
          throw new Error("Malformed provider fixture must create a default document.");
        }
        const response = await propose(app, jar, project.id, document.id, {
          operation: "continue",
          provider,
        });
        expect(response.statusCode, response.body).toBe(200);
        const job = response.json();
        expect(job).toMatchObject({ status: "failed", result: { proposal_markdown: "" } });
        expect(job.events.map((event: { status: string }) => event.status)).toEqual(["failed"]);
        for (const leaked of [
          JSON.stringify({ chapter_markdown: chapterMarkdown }),
          providerRawText,
        ]) {
          expect(response.body).not.toContain(leaked);
        }
        expect(await listRevisions(app, jar, project.id, document.id)).toHaveLength(1);
        const database = app.studioDb?.db;
        if (database === undefined) {
          throw new Error("Studio test app must expose its database.");
        }
        expect(database.select().from(usageEvents).all()).toHaveLength(0);
      } finally {
        await app.close();
      }
    },
  );

  it.each(transportRejectionCases)(
    "persists no TypeError credential diagnostic for $provider",
    async ({ provider, apiKey, prefix, error }) => {
      const { app } = await buildStudioApp(undefined, {
        textProviderFactory: transportRejectionFactory(provider, apiKey, prefix),
      });
      try {
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Transport rejection");
        const document = project.documents[0];
        if (document === undefined) {
          throw new Error("Transport rejection fixture must create a default document.");
        }
        const response = await propose(app, jar, project.id, document.id, {
          operation: "continue",
          provider,
        });
        expect(response.statusCode, response.body).toBe(200);
        const job = response.json();
        expect(job).toMatchObject({
          status: "failed",
          error,
          result: { proposal_markdown: "" },
        });
        expect(job.events).toEqual([
          expect.objectContaining({ status: "failed", details: { error } }),
        ]);
        expect(await listRevisions(app, jar, project.id, document.id)).toHaveLength(1);
        const database = app.studioDb?.db;
        if (database === undefined) throw new Error("Studio test app must expose its database.");
        expect(database.select().from(usageEvents).all()).toHaveLength(0);
        const persisted = database.select().from(jobs).all();
        expect(persisted).toHaveLength(1);
        expect(persisted[0]?.error).toBe(error);
        const serialized = [
          response.body,
          JSON.stringify(job),
          JSON.stringify(job.events),
          persisted[0]?.error,
        ].join("\n");
        for (const leaked of [apiKey, prefix]) expect(serialized).not.toContain(leaked);
      } finally {
        await app.close();
      }
    },
  );

  it("hides proposal jobs from other principals", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Scoped");
      const document = project.documents[0]!;
      const created = await propose(app, jar, project.id, document.id, { operation: "continue" });
      const job = created.json();

      const guest = await guestJar(app);
      const foreign = await call(
        app,
        guest,
        "POST",
        `/api/projects/${project.id}/ai-proposals/${job.id}/accept`,
      );
      expect(foreign.statusCode).toBe(404);
    } finally {
      await app.close();
    }
  });

  it("answers 404 when the job id names a job of another kind", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "WrongKind");
      const now = new Date();
      app
        .studioDb!.db.insert(jobs)
        .values({
          id: "job-export-1",
          project_id: project.id,
          kind: "export",
          operation: "export",
          status: "completed",
          created_at: now,
          updated_at: now,
        })
        .run();

      const response = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/ai-proposals/job-export-1/accept`,
      );
      expect(response.statusCode).toBe(404);
      expect(response.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
