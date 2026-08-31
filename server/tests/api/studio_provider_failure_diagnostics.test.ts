import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import { jobEvents, jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import {
  fixtureApiKey,
  hostileProviderFailureBody,
  PROVIDER_FAILURE_CANARIES,
} from "../credential_fixtures.js";
import { propose } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

type ProviderName = "dashscope" | "openai_compatible";
type Channel = "job response" | "SSE";

const PROVIDERS = [
  {
    provider: "dashscope",
    label: "DashScope",
    apiKey: fixtureApiKey("dashscope-http-credential", "that-must-not-leak"),
  },
  {
    provider: "openai_compatible",
    label: "OpenAI-compatible",
    apiKey: fixtureApiKey("openai-http-credential", "that-must-not-leak"),
  },
] as const;

interface FailureCase {
  readonly provider: ProviderName;
  readonly label: string;
  readonly apiKey: string;
  readonly channel: Channel;
  readonly status: number;
  readonly expectedAttempts: number;
}

const CASES: FailureCase[] = PROVIDERS.flatMap((providerCase) => [
  { ...providerCase, channel: "job response", status: 401, expectedAttempts: 1 },
  { ...providerCase, channel: "SSE", status: 401, expectedAttempts: 1 },
  { ...providerCase, channel: "job response", status: 503, expectedAttempts: 3 },
]);

function httpFailureFactory(
  provider: ProviderName,
  apiKey: string,
  status: number,
): { factory: TextGenerationProviderFactory; calls: () => number } {
  let calls = 0;
  const transport = async () => {
    calls += 1;
    return new Response(hostileProviderFailureBody(apiKey), {
      status,
      headers: { "content-type": "text/html" },
    });
  };
  const retry = { delayMs: 0, sleep: async () => {} };
  const factory: TextGenerationProviderFactory = (requested) => {
    if (requested !== provider) {
      throw new Error("HTTP failure fixture received an unexpected provider.");
    }
    return provider === "dashscope"
      ? new DashScopeTextProvider({ apiKey, retry, transport })
      : new OpenAICompatibleTextProvider({ apiKey, retry, transport });
  };
  return { factory, calls: () => calls };
}

function parseSingleErrorFrame(raw: string): unknown {
  expect(raw.endsWith("\n\n")).toBe(true);
  const frames = raw
    .split("\n\n")
    .filter((part) => part !== "")
    .map((part) => JSON.parse(part.slice("data: ".length)) as unknown);
  expect(frames).toHaveLength(1);
  return frames[0];
}

async function failureResponse(
  channel: Channel,
  app: Awaited<ReturnType<typeof buildStudioApp>>["app"],
  jar: Awaited<ReturnType<typeof ownerJar>>,
  projectId: string,
  documentId: string,
  provider: ProviderName,
): Promise<{ body: string; publicFailure: unknown }> {
  if (channel === "job response") {
    const response = await propose(app, jar, projectId, documentId, {
      operation: "continue",
      provider,
    });
    expect(response.statusCode, response.body).toBe(200);
    return { body: response.body, publicFailure: response.json() };
  }

  const response = await call(
    app,
    jar,
    "POST",
    `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`,
    { operation: "continue", provider },
  );
  expect(response.statusCode, response.body).toBe(200);
  return { body: response.body, publicFailure: parseSingleErrorFrame(response.body) };
}

describe("Provider failure diagnostics boundary", () => {
  it.each(CASES)(
    "discards $provider HTTP bodies across $channel, persistence, and later reads",
    async ({ provider, label, apiKey, channel, status, expectedAttempts }) => {
      const fixture = httpFailureFactory(provider, apiKey, status);
      const logs: string[] = [];
      const { app } = await buildStudioApp(undefined, {
        textProviderFactory: fixture.factory,
        logger: { level: "trace", stream: { write: (message) => logs.push(message) } },
      });
      try {
        const error = `${label} generation failed for step 'chapter_revision': provider returned HTTP ${status}.`;
        const jar = await ownerJar(app);
        const project = await seedProject(app, jar, "Provider HTTP failure");
        const document = project.documents[0];
        if (document === undefined) throw new Error("Expected a default document.");

        const response = await failureResponse(
          channel,
          app,
          jar,
          project.id,
          document.id,
          provider,
        );
        if (channel === "job response") {
          expect(response.publicFailure).toMatchObject({
            status: "failed",
            error,
            events: [expect.objectContaining({ details: { error } })],
          });
        } else {
          expect(response.publicFailure).toEqual({
            type: "error",
            error: { code: "PROVIDER_FAILED", message: error },
          });
        }

        const database = app.studioDb?.db;
        if (database === undefined) throw new Error("Expected the studio database.");
        const persistedJobs = database.select().from(jobs).all();
        const persistedEvents = database.select().from(jobEvents).all();
        expect(persistedJobs).toHaveLength(1);
        expect(persistedJobs[0]?.error).toBe(error);
        expect(persistedEvents).toHaveLength(1);
        expect(JSON.parse(persistedEvents[0]?.details_json ?? "{}")).toEqual({ error });
        expect(database.select().from(usageEvents).all()).toHaveLength(0);

        const listed = await call(app, jar, "GET", `/api/projects/${project.id}/jobs`);
        expect(listed.statusCode, listed.body).toBe(200);
        expect(listed.json().jobs).toEqual([
          expect.objectContaining({
            status: "failed",
            error,
            events: [expect.objectContaining({ details: { error } })],
          }),
        ]);

        expect(logs.length).toBeGreaterThan(0);
        expect(logs.some((line) => line.includes('"msg":"request completed"'))).toBe(true);
        const serialized = [
          response.body,
          JSON.stringify(response.publicFailure),
          persistedJobs[0]?.error,
          persistedEvents[0]?.details_json,
          listed.body,
          logs.join("\n"),
        ].join("\n");
        for (const leaked of [apiKey, ...PROVIDER_FAILURE_CANARIES, "[REDACTED]"]) {
          expect(serialized).not.toContain(leaked);
        }
        expect(fixture.calls()).toBe(expectedAttempts);
      } finally {
        await app.close();
      }
    },
  );
});
