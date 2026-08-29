import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import {
  authHeaders,
  buildStudioApp,
  call,
  type DocumentPayload,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const STREAM_PATH = (projectId: string, documentId: string) =>
  `/api/projects/${projectId}/documents/${documentId}/ai-proposals/stream`;

/** Split a buffered SSE response body into its JSON frames. */
function parseFrames(raw: string): ProposalStreamFrame[] {
  return raw
    .split("\n\n")
    .filter((part) => part !== "")
    .map((part) => JSON.parse(part.replace(/^data: /, "")) as ProposalStreamFrame);
}

/**
 * Route-level client-disconnect semantics (#393, #308): the route wires
 * `reply.raw` "close" to the disconnect signal, so an aborted stream must
 * persist nothing (no failed job, no usage event) and must release the
 * in-flight guard slot (a follow-up stream for the same document must not
 * answer 409).
 */
describe("proposal stream client disconnect (#393)", () => {
  it("persists nothing and releases the in-flight guard when the client closes mid-stream", async () => {
    // The provider yields one frame, pauses until the test releases it, then
    // finishes — so the "close" lands while a frame round-trip is in flight.
    let release: () => void = () => {};
    const released = new Promise<void>((resolve) => {
      release = resolve;
    });
    let firstYield: () => void = () => {};
    const yielded = new Promise<void>((resolve) => {
      firstYield = resolve;
    });
    let finish: () => void = () => {};
    const finished = new Promise<void>((resolve) => {
      finish = resolve;
    });
    async function* script(
      _task: TextGenerationTask,
      signal: AbortSignal | undefined,
    ): AsyncGenerator<string, void, void> {
      try {
        // Each delta is deliberately long: the landing path rejects
        // accumulated proposals of 400 characters or fewer as non-prose.
        yield "Rain fell over the harbor while the boats knocked against the pier. ".repeat(4);
        firstYield();
        await released;
        if (signal?.aborted === true) {
          yield "aborted";
          return;
        }
        yield "Lamplight spread across the wet cobblestones as the market closed. ".repeat(4);
      } finally {
        finish();
      }
    }

    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: () => ({
        generateStructured: async () => {
          throw new Error("the synchronous path must not run for the stream endpoint");
        },
        generateStructuredStreaming: (task, options) => script(task, options?.signal),
      }),
    });
    try {
      // Capture the hijacked raw reply once the request reaches the route so
      // the test can simulate the client dropping the connection mid-stream.
      let rawReply: import("node:http").ServerResponse | undefined;
      app.addHook("onRequest", async (_request, reply) => {
        rawReply = reply.raw;
      });

      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Disconnect");
      const document = project.documents[0] as DocumentPayload;
      const database = app.studioDb?.db;
      if (database === undefined) throw new Error("studio test app must expose its database");
      const usageBefore = database.select().from(usageEvents).all().length;

      const aborted = app.inject({
        method: "POST",
        url: STREAM_PATH(project.id, document.id),
        payload: { operation: "continue", provider: "mock" },
        headers: authHeaders(jar),
      });

      await yielded;
      // Let the first delta flush before simulating the TCP drop.
      await new Promise((resolve) => setTimeout(resolve, 25));
      expect(rawReply, "stream request must be in flight").toBeDefined();
      rawReply?.emit("close");
      release();

      // The simulated disconnect destroys the injected response, so the
      // inject promise rejects instead of yielding a response body.
      await expect(aborted).rejects.toThrow(/destroyed before completion/);
      await finished;

      // Nothing persisted for the aborted stream: no job row at all (a
      // failed job would mean the abort did not reach the landing path) and
      // no usage event.
      expect(database.select().from(jobs).all()).toHaveLength(0);
      expect(database.select().from(usageEvents).all()).toHaveLength(usageBefore);

      // The in-flight guard slot was released: the same document/operation
      // streams again instead of answering 409.
      const retry = await call(app, jar, "POST", STREAM_PATH(project.id, document.id), {
        operation: "continue",
        provider: "mock",
      });
      expect(retry.statusCode, retry.body).toBe(200);
      const frames = parseFrames(retry.body);
      expect(frames.at(-1)?.type).toBe("done");
      expect(
        database.select().from(usageEvents).all().length,
        "the retried stream lands its usage",
      ).toBe(usageBefore + 1);
      const jobRows = database.select().from(jobs).all();
      expect(jobRows).toHaveLength(1);
      expect((jobRows[0] as { status: string }).status).toBe("completed");
    } finally {
      await app.close();
    }
  });
});
