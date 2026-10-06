import { afterEach, describe, expect, it, vi } from "vitest";
import { ProposalOutcomeUnknownError, streamProposal } from "@/app/proposalStream";
import { job } from "@/test/factories";

const streamedJob = job({
  id: "job-9",
  model: "deterministic-story-v1",
  request: { operation: "continue" },
  result: { proposal_markdown: "Night fell over the harbor." },
  created_at: "2026-08-28T00:00:00Z",
  updated_at: "2026-08-28T00:00:00Z",
});

function sseResponse(frames: string[], status = 200): Response {
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
    status,
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

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("streamProposal deadline and anomaly diagnostics (DR-026)", () => {
  it("ignores server heartbeat comments and still resolves the done frame", async () => {
    const encoder = new TextEncoder();
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(
            new ReadableStream<Uint8Array>({
              start(controller) {
                controller.enqueue(
                  encoder.encode(
                    ': heartbeat\n\ndata: {"type":"delta","text":"Night fell "}\n\n: heartbeat\n\n' +
                      `data: ${JSON.stringify({ type: "done", job: streamedJob })}\n\n`,
                  ),
                );
                controller.close();
              },
            }),
            { status: 200, headers: { "Content-Type": "text/event-stream" } },
          ),
        ),
      ),
    );
    const deltas: string[] = [];

    await expect(
      streamProposal({ ...baseRequest(), onDelta: (text) => deltas.push(text) }),
    ).resolves.toEqual(streamedJob);
    expect(deltas).toEqual(["Night fell "]);
  });

  it("aborts a stream that stops delivering bytes and reports the silence", async () => {
    vi.useFakeTimers();
    const encoder = new TextEncoder();
    let streamSignal: AbortSignal | undefined;
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"delta","text":"Night fell "}\n\n'));
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((_path: string, init: RequestInit) => {
        streamSignal = init.signal ?? undefined;
        return Promise.resolve(
          new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } }),
        );
      }),
    );
    const logged = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const request = { ...baseRequest(), stallTimeoutMs: 30_000 };
    const settled = streamProposal(request).then(
      () => "resolved" as const,
      (error: unknown) => error,
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(await Promise.race([settled, Promise.resolve("pending" as const)])).toBe("pending");
    await vi.advanceTimersByTimeAsync(30_000);

    const outcome = await Promise.race([settled, Promise.resolve("pending" as const)]);
    expect(outcome).not.toBe("pending");
    expect(outcome).toBeInstanceOf(ProposalOutcomeUnknownError);
    expect(outcome).toMatchObject({
      cause: {
        name: "ProposalStreamStalledError",
        silenceMs: 30_000,
        deltaFrames: 1,
      },
    });
    expect((outcome as ProposalOutcomeUnknownError).message).toMatch(/no stream data/i);
    expect((outcome as ProposalOutcomeUnknownError).message).toMatch(/The outcome is unknown\./);
    expect(streamSignal?.aborted).toBe(true);
    expect(logged).toHaveBeenCalledWith(
      "[proposal-stream]",
      expect.stringContaining("stalled"),
      expect.objectContaining({ silenceMs: 30_000, deltaFrames: 1 }),
    );
  });

  it("reports how much arrived when the stream is interrupted before a terminal frame", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(sseResponse([JSON.stringify({ type: "delta", text: "Night fell " })])),
      ),
    );
    const logged = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    const failure = await streamProposal(baseRequest()).catch((reason: unknown) => reason);

    expect(failure).toBeInstanceOf(ProposalOutcomeUnknownError);
    expect((failure as ProposalOutcomeUnknownError).message).toMatch(/outcome is unknown/i);
    // 45 bytes = the 14-byte delta payload plus its `data: ` / blank-line frame.
    expect((failure as ProposalOutcomeUnknownError).message).toMatch(
      /1 delta frame, 45 bytes received/i,
    );
    expect(logged).toHaveBeenCalledWith(
      "[proposal-stream]",
      expect.stringContaining("interrupted"),
      expect.objectContaining({ deltaFrames: 1, receivedBytes: 45 }),
    );
  });
});
