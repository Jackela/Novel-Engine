import { once } from "node:events";
import { readFile, realpath, writeFile } from "node:fs/promises";
import { createServer, type Socket } from "node:net";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { WebSocket } from "ws";
import type {
  AgentEvent,
  AgentPermissionRequest,
} from "../../src/contexts/ai/application/ports/ai_operations.js";
import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { fakeAcp, stop, textChunk } from "./acp_provider_fixture.js";

const task: TextGenerationTask = {
  step: "chapter_draft",
  systemPrompt: "Only JSON",
  userPrompt: "Snow",
  responseSchema: { chapter_markdown: "string" },
  metadata: {},
};
interface RpcReply {
  id?: number;
  result?: unknown;
  error?: { code: number; message: string };
}
/** Exercise callbacks as agent-originated protocol requests, including their error envelopes. */
function peerRequest(
  socket: WebSocket,
  id: number,
  method: string,
  params: Record<string, unknown>,
): Promise<RpcReply> {
  return new Promise((resolve) => {
    const listener = (bytes: Buffer) => {
      const response: RpcReply = JSON.parse(bytes.toString());
      if (response.id !== id) return;
      socket.off("message", listener);
      resolve(response);
    };
    socket.on("message", listener);
    socket.send(JSON.stringify({ jsonrpc: "2.0", id, method, params }));
  });
}
function update(socket: WebSocket, value: Record<string, unknown>, sessionId = "session-1"): void {
  socket.send(
    JSON.stringify({
      jsonrpc: "2.0",
      method: "session/update",
      params: { sessionId, update: value },
    }),
  );
}

describe("ACP final callback ownership and safe evidence", () => {
  it("ignores another session and thoughts; sparse tool updates retain safe target and redact labels", async () => {
    const fixture = await fakeAcp((socket, message) => {
      update(
        socket,
        {
          sessionUpdate: "agent_message_chunk",
          content: { type: "text", text: "Cross-session injection" },
        },
        "another-session",
      );
      update(socket, {
        sessionUpdate: "agent_thought_chunk",
        content: { type: "text", text: "Private thought" },
      });
      update(socket, { sessionUpdate: "tool_call_update", toolCallId: "unknown-tool" });
      update(socket, {
        sessionUpdate: "tool_call",
        toolCallId: "tool",
        title: "Read\n token=hidden password=hidden secret=hidden sk-abcdefghijklmnop",
        kind: "read",
        status: "in_progress",
        locations: [{ path: "material.md" }],
        rawInput: { token: "raw-secret" },
      });
      update(socket, {
        sessionUpdate: "tool_call_update",
        toolCallId: "tool",
        status: "completed",
      });
      textChunk(socket, '{"chapter_markdown":"Only draft"}');
      stop(socket, message.id);
    });
    const events: AgentEvent[] = [];
    try {
      const result = await new AcpTextProvider(fixture.options).generateStructured(task, {
        onAgentEvent: (event) => events.push(event),
      });
      expect(result.content).toEqual({ chapter_markdown: "Only draft" });
      expect(events).toHaveLength(3);
      expect(events[0]).toMatchObject({ title: "Agent tool", kind: "other", status: "pending" });
      expect(events[2]).toMatchObject({
        tool_id: "tool",
        kind: "read",
        target: "material.md",
        status: "completed",
      });
      expect(JSON.stringify(events)).not.toMatch(
        /hidden|abcdefghijklmnop|raw-secret|Private thought|Cross-session/u,
      );
      expect(JSON.stringify(events)).toContain("[redacted]");
    } finally {
      await fixture.close();
    }
  });

  it("serves a bounded material read while denying file and permission requests from another session", async () => {
    const replies: RpcReply[] = [];
    let path = "";
    const fixture = await fakeAcp((socket, message) => {
      void (async () => {
        replies.push(
          await peerRequest(socket, 900, "fs/read_text_file", {
            sessionId: "session-1",
            path,
            line: 2,
            limit: 1,
          }),
        );
        replies.push(
          await peerRequest(socket, 901, "fs/read_text_file", { sessionId: "wrong-session", path }),
        );
        replies.push(
          await peerRequest(socket, 902, "fs/write_text_file", {
            sessionId: "wrong-session",
            path,
            content: "should-not-write",
          }),
        );
        replies.push(
          await peerRequest(socket, 903, "session/request_permission", {
            sessionId: "wrong-session",
            toolCall: { toolCallId: "tool" },
            options: [],
          }),
        );
        textChunk(socket, '{"chapter_markdown":"Draft"}');
        stop(socket, message.id);
      })().catch(() => socket.close());
    });
    path = join(await realpath(fixture.options.workspaceRoot ?? ""), "material.md");
    await writeFile(path, "first\nsecond\nthird");
    let permissionCalls = 0;
    try {
      await new AcpTextProvider(fixture.options).generateStructured(task, {
        requestPermission: async () => {
          permissionCalls++;
          return "allow";
        },
      });
      expect(replies[0]?.result).toEqual({ content: "second" });
      expect(
        replies
          .slice(1)
          .every((reply) => reply.error?.code === -32603 && reply.result === undefined),
      ).toBe(true);
      expect(await readFile(path, "utf8")).toBe("first\nsecond\nthird");
      expect(permissionCalls).toBe(0);
    } finally {
      await fixture.close();
    }
  });

  it("rejects unknown permission options in the callback without approving them", async () => {
    let reply: RpcReply | undefined;
    const requests: AgentPermissionRequest[] = [];
    const fixture = await fakeAcp((socket, message) => {
      void (async () => {
        reply = await peerRequest(socket, 900, "session/request_permission", {
          sessionId: "session-1",
          toolCall: { toolCallId: "tool", locations: [{ path: "../private.md" }] },
          options: [{ optionId: "deny", name: "Deny token=secret", kind: "reject_once" }],
        });
        textChunk(socket, '{"chapter_markdown":"Draft without permission"}');
        stop(socket, message.id);
      })().catch(() => socket.close());
    });
    try {
      await new AcpTextProvider(fixture.options).generateStructured(task, {
        requestPermission: async (request) => {
          requests.push(request);
          return "invented";
        },
      });
      expect(reply?.error?.code).toBe(-32603);
      expect(reply?.result).toBeUndefined();
      expect(requests[0]).toMatchObject({
        tool: { title: "Agent tool", kind: "other" },
        options: [{ option_id: "deny", name: "Deny [redacted]", kind: "reject_once" }],
      });
      expect(requests[0]?.tool.target).toBeUndefined();
    } finally {
      await fixture.close();
    }
  });

  it("a declined permission cancels the submitted turn instead of hanging or retrying", async () => {
    const fixture = await fakeAcp((socket) =>
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 900,
          method: "session/request_permission",
          params: {
            sessionId: "session-1",
            toolCall: { toolCallId: "tool" },
            options: [{ optionId: "allow", name: "Allow", kind: "allow_once" }],
          },
        }),
      ),
    );
    try {
      await expect(
        new AcpTextProvider(fixture.options).generateStructured(task, {
          requestPermission: async () => null,
        }),
      ).rejects.toThrow("cancelled");
      expect(
        fixture.messages.filter((message) => message.method === "session/prompt"),
      ).toHaveLength(1);
    } finally {
      await fixture.close();
    }
  });

  it("an observer failure remains visible and cannot become a successful prompt", async () => {
    const fixture = await fakeAcp((socket) =>
      update(socket, {
        sessionUpdate: "tool_call",
        toolCallId: "tool",
        title: "Read material",
        kind: "read",
        status: "pending",
      }),
    );
    try {
      await expect(
        new AcpTextProvider(fixture.options).generateStructured(task, {
          onAgentEvent: () => {
            throw new Error("Observer unavailable");
          },
        }),
      ).rejects.toThrow("Observer unavailable");
      expect(
        fixture.messages.filter((message) => message.method === "session/prompt"),
      ).toHaveLength(1);
    } finally {
      await fixture.close();
    }
  });
  it("rejects an already aborted request without a submitted prompt or unhandled transport error", async () => {
    const fixture = await fakeAcp(() => {});
    const abort = new AbortController();
    abort.abort();
    try {
      await expect(
        new AcpTextProvider(fixture.options).generateStructured(task, { signal: abort.signal }),
      ).rejects.toThrow("cancelled");
      expect(fixture.messages.some((entry) => entry.method === "session/prompt")).toBe(false);
    } finally {
      await fixture.close();
    }
  });

  it.each(["cancel", "timeout"])(
    "handles %s safely before the WebSocket upgrade completes",
    async (mode) => {
      const fixture = await fakeAcp(() => {});
      const sockets = new Set<Socket>();
      let accepted = () => {};
      const started = new Promise<void>((resolve) => {
        accepted = resolve;
      });
      const server = createServer((socket) => {
        sockets.add(socket);
        socket.once("data", accepted);
      });
      server.listen(0, "127.0.0.1");
      await once(server, "listening");
      const address = server.address();
      if (address === null || typeof address === "string") throw new Error("Expected TCP address");
      const abort = new AbortController();
      try {
        const pending = new AcpTextProvider({
          ...fixture.options,
          proxyUrl: `ws://127.0.0.1:${address.port}/acp`,
          handshakeMs: mode === "cancel" ? 2000 : 80,
        }).generateStructured(task, { signal: abort.signal });
        const cancelled = expect(pending).rejects.toThrow(
          mode === "cancel" ? "cancelled" : "timeout",
        );
        await started;
        if (mode === "cancel") abort.abort();
        await cancelled;
        expect(fixture.messages).toHaveLength(0);
      } finally {
        for (const socket of sockets) socket.destroy();
        await new Promise<void>((resolve) => server.close(() => resolve()));
        await fixture.close();
      }
    },
  );
});
