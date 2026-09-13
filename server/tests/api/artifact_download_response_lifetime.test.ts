import { EventEmitter } from "node:events";

import { describe, expect, it, vi } from "vitest";

import { sendWithinArtifactResponseLifetime } from "../../src/contexts/studio/interface/http/artifact_download_response_lifetime.js";

class FakeResponse extends EventEmitter {
  destroyed = false;
  closed = false;
  writableFinished = false;
}

describe("artifact download response lifetime", () => {
  it.each(["finish", "close"] as const)("settles once on response %s", async (event) => {
    const response = new FakeResponse();
    const socket = new EventEmitter();
    const send = vi.fn();
    const pending = sendWithinArtifactResponseLifetime({ response, socket, send });

    expect(send).toHaveBeenCalledTimes(1);
    response.emit(event);
    response.emit("finish");
    response.emit("close");
    socket.emit("close");
    await expect(pending).resolves.toBeUndefined();
    expect(response.eventNames()).toEqual([]);
    expect(socket.eventNames()).toEqual([]);
  });

  it("settles on socket disconnect and rejects the exact response error", async () => {
    const disconnectedResponse = new FakeResponse();
    const socket = new EventEmitter();
    const disconnected = sendWithinArtifactResponseLifetime({
      response: disconnectedResponse,
      socket,
      send: () => {},
    });
    socket.emit("close");
    await expect(disconnected).resolves.toBeUndefined();

    const failedResponse = new FakeResponse();
    const failure = new Error("response failed");
    const failed = sendWithinArtifactResponseLifetime({
      response: failedResponse,
      send: () => {},
    });
    failedResponse.emit("error", failure);
    await expect(failed).rejects.toBe(failure);
  });

  it("handles synchronous send completion and failure without leaking listeners", async () => {
    const completed = new FakeResponse();
    await expect(
      sendWithinArtifactResponseLifetime({
        response: completed,
        send: () => {
          completed.writableFinished = true;
        },
      }),
    ).resolves.toBeUndefined();
    expect(completed.eventNames()).toEqual([]);

    const failed = new FakeResponse();
    const failure = new Error("send failed");
    await expect(
      sendWithinArtifactResponseLifetime({
        response: failed,
        send: () => {
          throw failure;
        },
      }),
    ).rejects.toBe(failure);
    expect(failed.eventNames()).toEqual([]);
  });

  it.each(["response", "request", "socket"] as const)(
    "settles without sending when the %s closed before listener registration",
    async (closedOwner) => {
      const response = new FakeResponse();
      const request = Object.assign(new EventEmitter(), { aborted: false, destroyed: false });
      const socket = Object.assign(new EventEmitter(), { destroyed: false, closed: false });
      if (closedOwner === "response") response.destroyed = true;
      if (closedOwner === "request") request.aborted = true;
      if (closedOwner === "socket") socket.destroyed = true;
      const send = vi.fn();

      await expect(
        sendWithinArtifactResponseLifetime({ response, request, socket, send }),
      ).resolves.toBeUndefined();
      expect(send).not.toHaveBeenCalled();
      expect(response.eventNames()).toEqual([]);
      expect(request.eventNames()).toEqual([]);
      expect(socket.eventNames()).toEqual([]);
    },
  );
});
