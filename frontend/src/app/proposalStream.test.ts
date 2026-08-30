import { afterEach, describe, expect, it, vi } from "vitest";

import { job } from "@/test/factories";

import { HttpError } from "./api";
import { ProposalStreamParser, streamProposal } from "./proposalStream";

afterEach(() => {
  vi.unstubAllGlobals();
});

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

function stubFetch(response: Response | Error): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      response instanceof Response ? Promise.resolve(response) : Promise.reject(response),
    ),
  );
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

describe("ProposalStreamParser", () => {
  it("assembles frames split across chunks and buffers partial events", () => {
    const parser = new ProposalStreamParser();
    expect(parser.append('data: {"type":"del')).toEqual([]);
    expect(parser.append('ta","text":"A"}\n\ndata: {"type":"del')).toEqual([
      { type: "delta", text: "A" },
    ]);
    expect(parser.append('ta","text":"B"}\n\n')).toEqual([{ type: "delta", text: "B" }]);
  });

  it("joins multi-line data fields and skips foreign SSE fields", () => {
    const parser = new ProposalStreamParser();
    const frames = parser.append(': ping\nevent: x\ndata: {"type":"delta",\ndata: "text":"C"}\n\n');
    expect(frames).toEqual([{ type: "delta", text: "C" }]);
  });

  it("ignores frames with an unknown type", () => {
    const parser = new ProposalStreamParser();
    const frames = parser.append(
      'data: {"type":"tick","at":1}\n\ndata: {"type":"delta","text":"D"}\n\n',
    );
    expect(frames).toEqual([{ type: "delta", text: "D" }]);
  });

  it.each([
    ["non-JSON payload", "not-json", /not JSON/],
    ["JSON array", "[1,2]", /proposal frame/],
    ["delta missing text", '{"type":"delta"}', /delta\.text/],
    ["delta with non-string text", '{"type":"delta","text":42}', /delta\.text/],
    ["error frame missing code", '{"type":"error","error":{"message":"x"}}', /error\.code/],
    [
      "error frame missing message",
      '{"type":"error","error":{"code":"PROVIDER_FAILED"}}',
      /error\.message/,
    ],
    ["done frame missing job", '{"type":"done"}', /done\.job/],
  ])("rejects malformed frame: %s", (_name, data, pattern) => {
    const parser = new ProposalStreamParser();
    expect(() => parser.append(`data: ${data}\n\n`)).toThrow(pattern);
  });
});

describe("streamProposal", () => {
  it("relays deltas, keeps credentials/CSRF semantics, and resolves the done-frame job", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        sseResponse([
          JSON.stringify({ type: "delta", text: "Night fell " }),
          JSON.stringify({ type: "delta", text: "over the harbor." }),
          JSON.stringify({ type: "done", job: streamedJob }),
        ]),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const deltas: string[] = [];

    const job = await streamProposal({
      ...baseRequest(),
      onDelta: (text) => deltas.push(text),
    });

    expect(deltas).toEqual(["Night fell ", "over the harbor."]);
    expect(job).toEqual(streamedJob);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/documents/document-1/ai-proposals/stream",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          operation: "continue",
          instruction: "Polish",
          provider: "mock",
        }),
      }),
    );
  });

  it("rejects with the error-frame message and code", async () => {
    stubFetch(
      sseResponse([
        JSON.stringify({ type: "delta", text: "partial" }),
        JSON.stringify({
          type: "error",
          error: { code: "PROVIDER_FAILED", message: "stream exploded" },
        }),
      ]),
    );
    const failure = streamProposal(baseRequest()).catch((reason: unknown) => reason);
    await expect(failure).resolves.toMatchObject({
      message: "stream exploded",
      code: "PROVIDER_FAILED",
    });
    await expect(failure).resolves.toBeInstanceOf(HttpError);
  });

  it("reads the envelope error returned before the stream starts", async () => {
    stubFetch(
      new Response(
        JSON.stringify({
          error: { code: "INVALID_OPERATION", message: "nope" },
        }),
        {
          status: 422,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    const failure = streamProposal(baseRequest()).catch((reason: unknown) => reason);
    await expect(failure).resolves.toBeInstanceOf(HttpError);
    const error = (await failure) as HttpError;
    expect(error.status).toBe(422);
    expect(error.message).toBe("nope");
  });

  it("rejects when the stream ends without a terminal frame", async () => {
    stubFetch(sseResponse([JSON.stringify({ type: "delta", text: "partial" })]));
    await expect(streamProposal(baseRequest())).rejects.toThrow(/ended without a result/);
  });

  it("translates an aborted stream into a cancellation error", async () => {
    stubFetch(new DOMException("The operation was aborted.", "AbortError"));
    await expect(streamProposal(baseRequest())).rejects.toThrow("Request cancelled.");
  });

  it("forwards the caller signal to fetch", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn((_path: string, _init: RequestInit) =>
      Promise.resolve(sseResponse([])),
    );
    vi.stubGlobal("fetch", fetchMock);
    const failure = streamProposal({
      ...baseRequest(),
      signal: controller.signal,
    }).catch((reason: unknown) => reason);
    await expect(failure).resolves.toBeInstanceOf(HttpError);
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(controller.signal);
  });
});
