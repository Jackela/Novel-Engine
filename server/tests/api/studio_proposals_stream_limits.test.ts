import { describe, expect, it } from "vitest";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { OpenAICompatibleTextProvider } from "../../src/contexts/ai/infrastructure/providers/openai_compatible_provider.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import {
  buildStudioApp,
  call,
  type DocumentPayload,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const STREAM_PATH = (projectId: string, documentId: string) =>
  `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`;

function oversizedStreamingFactory(): TextGenerationProviderFactory {
  return () => {
    const provider: TextGenerationProvider = {
      generateStructured: async () => {
        throw new Error("the synchronous path must not run");
      },
      async *generateStructuredStreaming() {
        yield `#\n${"a".repeat(999_997)}\ud83d`;
        yield "\ude00";
        yield "b";
        yield "must not escape";
      },
    };
    return provider;
  };
}

function failingBodyFactory(diagnostic: string): TextGenerationProviderFactory {
  return () => {
    let reads = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        reads += 1;
        if (reads === 1) {
          controller.enqueue(
            new TextEncoder().encode(
              `data: ${JSON.stringify({ choices: [{ delta: { content: "# Chapter\nSafe start." } }] })}\n\n`,
            ),
          );
          return;
        }
        controller.error(new TypeError(`upstream read exposed ${diagnostic}`));
      },
    });
    return new OpenAICompatibleTextProvider({
      apiKey: fixtureApiKey("sk-openai", "stream-body-failure"),
      transport: () => Promise.resolve(new Response(body, { status: 200 })),
    });
  };
}

function parseFrames(raw: string): ProposalStreamFrame[] {
  return raw
    .split("\n\n")
    .filter((part) => part !== "")
    .map((part) => JSON.parse(part.slice("data: ".length)) as ProposalStreamFrame);
}

describe("proposal stream semantic size boundary", () => {
  it("stops before the crossing delta and lands one failed job without usage", async () => {
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: oversizedStreamingFactory(),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Oversized stream");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "mock",
      });

      expect(response.statusCode).toBe(200);
      const frames = parseFrames(response.body);
      expect(frames.map((frame) => frame.type)).toEqual(["delta", "delta", "error"]);
      const first = frames[0];
      if (first?.type !== "delta") throw new Error("expected one safe delta");
      expect(first.text).toHaveLength(1_000_000);
      const second = frames[1];
      if (second?.type !== "delta") throw new Error("expected the paired surrogate delta");
      expect(second.text).toBe("\ude00");
      const terminal = frames[2];
      if (terminal?.type !== "error") throw new Error("expected a terminal error frame");
      expect(terminal.error.message).toMatch(/exceeds 1,000,000 Unicode code point limit/);

      const rows = database.select().from(jobs).all();
      expect(rows).toHaveLength(1);
      expect(rows[0]).toMatchObject({ status: "failed" });
      expect(JSON.parse((rows[0] as { result_json: string }).result_json)).toMatchObject({
        proposal_markdown: "",
      });
      expect(database.select().from(usageEvents).all()).toHaveLength(0);
    } finally {
      await app.close();
    }
  });

  it("lands a sanitized failed job when the upstream body reader fails mid-stream", async () => {
    const diagnostic = "private-provider-diagnostic";
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: failingBodyFactory(diagnostic),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Body reader failure");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");

      const response = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "openai_compatible",
      });

      expect(response.statusCode).toBe(200);
      const frames = parseFrames(response.body);
      expect(frames.map((frame) => frame.type)).toEqual(["delta", "error"]);
      const terminal = frames[1];
      if (terminal?.type !== "error") throw new Error("expected a terminal error frame");
      expect(terminal.error.message).toMatch(/transport request failed/);
      expect(terminal.error.message).not.toContain(diagnostic);

      const rows = database.select().from(jobs).all();
      expect(rows).toHaveLength(1);
      expect(rows[0]).toMatchObject({ status: "failed" });
      expect((rows[0] as { error: string }).error).not.toContain(diagnostic);
      expect(JSON.parse((rows[0] as { result_json: string }).result_json)).toMatchObject({
        proposal_markdown: "",
      });
      expect(database.select().from(usageEvents).all()).toHaveLength(0);
    } finally {
      await app.close();
    }
  });
});
