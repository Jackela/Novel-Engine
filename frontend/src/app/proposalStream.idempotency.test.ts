import { afterEach, describe, expect, it, vi } from "vitest";

import { job } from "@/test/factories";

import { streamProposal } from "./proposalStream";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const streamedJob = job({
  id: "job-9",
  request: { operation: "continue" },
  result: { proposal_markdown: "Night fell over the harbor." },
  created_at: "2026-08-28T00:00:00Z",
  updated_at: "2026-08-28T00:00:00Z",
});

function sseResponse(frames: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(`data: ${frame}\n\n`));
      }
      controller.close();
    },
  });
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function baseRequest(): Parameters<typeof streamProposal>[0] {
  return {
    projectId: "project-1",
    documentId: "document-1",
    operation: "continue",
    instruction: "Polish",
    provider: "mock",
    onDelta: () => {},
  };
}

/**
 * DR-027: the durable key travels in the request header, so a resend carrying
 * the same key replays the server's job instead of drafting a second one.
 */
describe("streamProposal generation idempotency (DR-027)", () => {
  it("sends the durable generation key header when one is provided", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(sseResponse([JSON.stringify({ type: "done", job: streamedJob })])),
    );
    vi.stubGlobal("fetch", fetchMock);

    await streamProposal({ ...baseRequest(), idempotencyKey: "attempt-key-1" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/documents/document-1/ai-proposals/stream",
      expect.objectContaining({
        headers: expect.objectContaining({ "Idempotency-Key": "attempt-key-1" }),
      }),
    );
  });

  it("omits the durable generation key header when no key is provided", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(sseResponse([JSON.stringify({ type: "done", job: streamedJob })])),
    );
    vi.stubGlobal("fetch", fetchMock);

    await streamProposal(baseRequest());

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/documents/document-1/ai-proposals/stream",
      expect.objectContaining({
        headers: expect.not.objectContaining({ "Idempotency-Key": expect.anything() }),
      }),
    );
  });
});
