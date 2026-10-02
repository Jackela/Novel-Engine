import { EventEmitter } from "node:events";

import { afterEach, describe, expect, it, vi } from "vitest";

import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { writeProposalStreamResponse } from "../../src/contexts/studio/interface/http/proposal_stream_response.js";
import {
  FakeResponse,
  flushMicrotasks,
  scriptedFrames,
} from "./proposal_stream_response_helpers.js";

/**
 * DR-026: a committed proposal stream beats a `: heartbeat` comment while it
 * waits for the next frame, so a long provider silence cannot look like a dead
 * connection to a proxy or to the browser.
 */
describe("proposal stream response heartbeat", () => {
  afterEach(() => vi.useRealTimers());

  it("writes comment heartbeats while the next frame is pending", async () => {
    vi.useFakeTimers();
    const response = new FakeResponse();
    let release: (() => void) | undefined;
    const pending = new Promise<IteratorResult<ProposalStreamFrame, void>>((resolve) => {
      release = () => resolve({ done: true, value: undefined });
    });
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "one" } },
      { done: true, value: undefined },
    ]);
    frames.next.mockImplementationOnce(async () => ({
      done: false,
      value: { type: "delta", text: "one" },
    }));
    frames.next.mockImplementationOnce(() => pending);
    const writing = writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect: new AbortController(),
      hijack: () => {},
      heartbeatMs: 1_000,
    });
    await flushMicrotasks();

    expect(response.chunks).toEqual(['data: {"type":"delta","text":"one"}\n\n']);
    await vi.advanceTimersByTimeAsync(999);
    expect(response.chunks).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(response.chunks).toHaveLength(2);
    expect(response.chunks[1]).toBe(": heartbeat\n\n");
    await vi.advanceTimersByTimeAsync(2_000);
    expect(response.chunks.filter((chunk) => chunk === ": heartbeat\n\n")).toHaveLength(3);

    release?.();
    await writing;

    expect(response.writableFinished).toBe(true);
    expect(frames.next).toHaveBeenCalledTimes(2);
    expect(frames.return).toHaveBeenCalledTimes(1);
  });

  it("keeps the heartbeat out of the stream after the terminal frame", async () => {
    vi.useFakeTimers();
    const response = new FakeResponse();
    const frames = scriptedFrames([
      { done: false, value: { type: "delta", text: "one" } },
      { done: true, value: undefined },
    ]);

    await writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect: new AbortController(),
      hijack: () => {},
      heartbeatMs: 1_000,
    });
    await vi.advanceTimersByTimeAsync(5_000);

    expect(response.chunks).toEqual(['data: {"type":"delta","text":"one"}\n\n']);
    expect(response.writableFinished).toBe(true);
  });
});
