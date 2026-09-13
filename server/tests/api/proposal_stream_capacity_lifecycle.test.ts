import { EventEmitter } from "node:events";

import { describe, expect, it, vi } from "vitest";

import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { OperationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";
import { writeProposalStreamResponse } from "../../src/contexts/studio/interface/http/proposal_stream_response.js";
import { releaseProposalStreamSession } from "./proposal_stream_session_helpers.js";

class CapacityLifecycleResponse extends EventEmitter {
  writableFinished = false;

  constructor(
    private readonly acceptsWrite: boolean,
    private readonly onEnd: () => void = () => {},
  ) {
    super();
  }

  writeHead(): this {
    return this;
  }

  write(): boolean {
    return this.acceptsWrite;
  }

  end(): this {
    this.onEnd();
    this.writableFinished = true;
    return this;
  }

  destroy(): this {
    return this;
  }
}

function terminalFrames(
  onCleanup: () => void = () => {},
): AsyncGenerator<ProposalStreamFrame, void, void> {
  return (async function* () {
    try {
      yield { type: "error", error: { code: "PROVIDER_FAILED", message: "known failure" } };
    } finally {
      onCleanup();
    }
  })();
}

function capacityProbe() {
  const guard = new InFlightOperationGuard({ applicationLimit: 1, projectLimit: 1 });
  const permit = guard.acquire({
    projectId: "active-project",
    documentId: "active-document",
    operation: "continue",
  });
  const nextTarget = {
    projectId: "next-project",
    documentId: null,
    operation: "review",
  } as const;
  return {
    release: () => permit.release(),
    expectBlocked: () =>
      expect(() => guard.acquire(nextTarget)).toThrow(OperationCapacityExceededError),
    expectAvailable: () => guard.acquire(nextTarget).release(),
  };
}

describe("proposal stream capacity lifetime", () => {
  it("returns and releases once without starting or hijacking an already-aborted stream", async () => {
    let started = false;
    async function* neverStartedFrames(): AsyncGenerator<ProposalStreamFrame, void, void> {
      started = true;
      yield { type: "delta", text: "must not start" };
    }
    const frames = neverStartedFrames();
    const next = vi.spyOn(frames, "next");
    const returned = vi.spyOn(frames, "return");
    const hijack = vi.fn();
    const releaseCapacity = vi.fn();
    const disconnect = new AbortController();
    disconnect.abort();

    await writeProposalStreamResponse({
      response: new CapacityLifecycleResponse(true),
      frames,
      disconnect,
      hijack,
      releaseCapacity,
    });

    expect(started).toBe(false);
    expect(next).not.toHaveBeenCalled();
    expect(hijack).not.toHaveBeenCalled();
    expect(returned).toHaveBeenCalledOnce();
    expect(releaseCapacity).toHaveBeenCalledOnce();
  });

  it("releases the actual permit when a primary stream error and generator cleanup both fail", async () => {
    const capacity = capacityProbe();
    const releaseCapacity = vi.fn(capacity.release);
    const primaryError = new Error("primary stream failure");
    const cleanupError = new Error("generator cleanup failure");
    async function* failingFrames(): AsyncGenerator<ProposalStreamFrame, void, void> {
      yield await Promise.reject<ProposalStreamFrame>(primaryError);
    }
    const frames = failingFrames();
    const returned = vi.spyOn(frames, "return").mockImplementationOnce(async () => {
      expect(releaseCapacity).not.toHaveBeenCalled();
      capacity.expectBlocked();
      throw cleanupError;
    });
    const hijack = vi.fn();

    const failure = await writeProposalStreamResponse({
      response: new CapacityLifecycleResponse(true),
      frames,
      disconnect: new AbortController(),
      hijack,
      releaseCapacity,
    }).catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(AggregateError);
    if (!(failure instanceof AggregateError)) throw failure;
    expect(failure.errors).toEqual([primaryError, cleanupError]);
    expect(hijack).not.toHaveBeenCalled();
    expect(returned).toHaveBeenCalledOnce();
    expect(releaseCapacity).toHaveBeenCalledOnce();
    capacity.expectAvailable();
  });

  it("releases a session permit even when the test cleanup helper sees return fail", async () => {
    const capacity = capacityProbe();
    const releaseCapacity = vi.fn(capacity.release);
    const cleanupError = new Error("test generator cleanup failure");
    const frames = terminalFrames();
    vi.spyOn(frames, "return").mockRejectedValueOnce(cleanupError);

    await expect(releaseProposalStreamSession({ frames, releaseCapacity })).rejects.toBe(
      cleanupError,
    );

    expect(releaseCapacity).toHaveBeenCalledOnce();
    capacity.expectAvailable();
  });

  it("releases only after an accepted terminal write is ended and returned", async () => {
    const capacity = capacityProbe();
    const releaseCapacity = vi.fn(capacity.release);
    const generatorCleanup = vi.fn();
    const response = new CapacityLifecycleResponse(true, () => {
      expect(releaseCapacity).not.toHaveBeenCalled();
      capacity.expectBlocked();
    });

    await writeProposalStreamResponse({
      response,
      frames: terminalFrames(generatorCleanup),
      disconnect: new AbortController(),
      hijack: () => {},
      releaseCapacity,
    });

    expect(response.writableFinished).toBe(true);
    expect(generatorCleanup).toHaveBeenCalledOnce();
    expect(releaseCapacity).toHaveBeenCalledOnce();
    capacity.expectAvailable();
  });

  it("keeps capacity while a terminal write waits for drain", async () => {
    const capacity = capacityProbe();
    const releaseCapacity = vi.fn(capacity.release);
    const response = new CapacityLifecycleResponse(false);
    const writing = writeProposalStreamResponse({
      response,
      frames: terminalFrames(),
      disconnect: new AbortController(),
      hijack: () => {},
      releaseCapacity,
    });

    await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(1));
    expect(releaseCapacity).not.toHaveBeenCalled();
    capacity.expectBlocked();
    response.emit("drain");
    await writing;

    expect(releaseCapacity).toHaveBeenCalledOnce();
    capacity.expectAvailable();
  });

  it("releases after disconnect cleanup and connection-listener disposal", async () => {
    let finishCleanup = (): void => {};
    let announceCleanup = (): void => {};
    const cleanupStarted = new Promise<void>((resolve) => {
      announceCleanup = resolve;
    });
    async function* interruptedFrames(): AsyncGenerator<ProposalStreamFrame, void, void> {
      try {
        yield { type: "delta", text: "pending" };
      } finally {
        announceCleanup();
        await new Promise<void>((resolve) => {
          finishCleanup = resolve;
        });
      }
    }
    const response = new CapacityLifecycleResponse(false);
    const socket = new EventEmitter();
    const capacity = capacityProbe();
    const releaseCapacity = vi.fn(() => {
      expect(response.listenerCount("close")).toBe(0);
      expect(response.listenerCount("error")).toBe(0);
      expect(socket.listenerCount("close")).toBe(0);
      capacity.release();
    });
    const writing = writeProposalStreamResponse({
      response,
      socket,
      frames: interruptedFrames(),
      disconnect: new AbortController(),
      hijack: () => {},
      releaseCapacity,
    });

    await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(1));
    response.emit("close");
    await cleanupStarted;
    await vi.waitFor(() => expect(response.listenerCount("drain")).toBe(0));
    expect(releaseCapacity).not.toHaveBeenCalled();
    capacity.expectBlocked();

    finishCleanup();
    await writing;
    expect(releaseCapacity).toHaveBeenCalledOnce();
    capacity.expectAvailable();
  });
});
