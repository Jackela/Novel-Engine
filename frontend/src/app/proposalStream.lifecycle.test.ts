import { afterEach, describe, expect, it, vi } from "vitest";

import { job } from "@/test/factories";

import { HttpError } from "./api";
import { ProposalOutcomeUnknownError, streamProposal } from "./proposalStream";

const streamedJob = job({
  id: "job-9",
  model: "deterministic-story-v1",
  request: { operation: "continue" },
  result: { proposal_markdown: "Night fell over the harbor." },
  created_at: "2026-08-28T00:00:00Z",
  updated_at: "2026-08-28T00:00:00Z",
});

function baseRequest(): Parameters<typeof streamProposal>[0] {
  return {
    projectId: "project-1",
    documentId: "document-1",
    operation: "continue",
    instruction: "Polish",
    provider: "mock",
    onDelta: () => undefined,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("streamProposal reader lifecycle", () => {
  it("cancels unread data and releases the reader lock after a parsed done frame", async () => {
    const encoder = new TextEncoder();
    const cancel = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const releaseLock = vi.fn();
    const read = vi
      .fn<() => Promise<ReadableStreamReadResult<Uint8Array>>>()
      .mockResolvedValueOnce({
        done: false,
        value: encoder.encode(`data: ${JSON.stringify({ type: "done", job: streamedJob })}\n\n`),
      })
      .mockResolvedValueOnce({
        done: false,
        value: encoder.encode('data: {"type":"delta","text":"late"}\n\n'),
      });
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: { getReader: () => ({ read, cancel, releaseLock }) },
        } as unknown as Response),
      ),
    );

    await expect(streamProposal(baseRequest())).resolves.toEqual(streamedJob);
    expect(read).toHaveBeenCalledTimes(1);
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(releaseLock).toHaveBeenCalledTimes(1);
  });

  it("cancels unread data and releases the reader lock after a parsed error frame", async () => {
    const encoder = new TextEncoder();
    const cancel = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const releaseLock = vi.fn();
    const read = vi.fn<() => Promise<ReadableStreamReadResult<Uint8Array>>>().mockResolvedValue({
      done: false,
      value: encoder.encode(
        `data: ${JSON.stringify({
          type: "error",
          error: { code: "PROVIDER_FAILED", message: "stream exploded" },
        })}\n\n`,
      ),
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: { getReader: () => ({ read, cancel, releaseLock }) },
        } as unknown as Response),
      ),
    );

    const failure = streamProposal(baseRequest()).catch((reason: unknown) => reason);
    await expect(failure).resolves.toBeInstanceOf(HttpError);
    await expect(failure).resolves.not.toBeInstanceOf(ProposalOutcomeUnknownError);
    expect(cancel).toHaveBeenCalledTimes(1);
    expect(releaseLock).toHaveBeenCalledTimes(1);
  });
});
