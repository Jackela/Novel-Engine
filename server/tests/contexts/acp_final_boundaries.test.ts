import { once } from "node:events";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { WebSocketServer } from "ws";
import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { type FakeAcpMessage, fakeAcp, stop, textChunk } from "./acp_provider_fixture.js";

const task: TextGenerationTask = {
  step: "chapter_draft",
  systemPrompt: "Only JSON",
  userPrompt: "Snow",
  responseSchema: { chapter_markdown: "string" },
  metadata: {},
};
const model = (value: string) => [
  {
    id: "model",
    name: "Model",
    category: "model",
    type: "select",
    currentValue: value,
    options: [{ value, name: value }],
  },
];

/** Negotiate over a real transport so missing or rejected model facts cannot be silently invented. */
async function negotiatedAgent(mode: string) {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-negotiation-"));
  const tokenFile = join(directory, "proxy-key");
  await writeFile(tokenFile, "test-only-token");
  const server = new WebSocketServer({ port: 0, host: "127.0.0.1" });
  await once(server, "listening");
  const messages: FakeAcpMessage[] = [];
  server.on("connection", (socket) =>
    socket.on("message", (bytes) => {
      const message: FakeAcpMessage = JSON.parse(bytes.toString());
      messages.push(message);
      const reply = (result: unknown) =>
        socket.send(JSON.stringify({ jsonrpc: "2.0", id: message.id, result }));
      if (message.method === "initialize") {
        if (mode !== "handshake-timeout")
          reply({
            protocolVersion: 1,
            agentCapabilities: {},
            authMethods: mode === "no-auth" ? [] : [{ id: "cached_token", name: "Cached" }],
          });
      } else if (message.method === "authenticate") reply({});
      else if (message.method === "session/new")
        reply({
          sessionId: "session-1",
          configOptions: ["unknown-model", "unsupported-override"].includes(mode)
            ? []
            : model("initial-model"),
        });
      else if (message.method === "session/set_config_option")
        reply({
          configOptions: model(mode === "rejected-override" ? "initial-model" : "chosen-model"),
        });
      else if (message.method === "session/prompt") {
        if (mode === "protocol-error")
          socket.send(
            JSON.stringify({
              jsonrpc: "2.0",
              id: message.id,
              error: { code: -32001, message: "token=never-expose" },
            }),
          );
        else {
          if (mode === "updated-model")
            socket.send(
              JSON.stringify({
                jsonrpc: "2.0",
                method: "session/update",
                params: {
                  sessionId: "session-1",
                  update: {
                    sessionUpdate: "config_option_update",
                    configOptions: model("actual-model"),
                  },
                },
              }),
            );
          textChunk(socket, '{"chapter_markdown":"Draft"}');
          reply({
            stopReason: "end_turn",
            usage: { inputTokens: 12, outputTokens: 4, totalTokens: 16 },
          });
        }
      }
    }),
  );
  const address = server.address();
  if (address === null || typeof address === "string") throw new Error("Expected socket address");
  return {
    messages,
    options: {
      proxyUrl: `ws://127.0.0.1:${address.port}/acp`,
      tokenFile,
      workspaceRoot: directory,
      command: "fake",
      args: [],
      handshakeMs: 100,
      executionMs: 300,
      overallMs: 1000,
    },
    close: async () => {
      for (const socket of server.clients) socket.terminate();
      await new Promise<void>((resolve) => server.close(() => resolve()));
      await rm(directory, { recursive: true, force: true });
    },
  };
}

describe("ACP final negotiation and turn boundaries", () => {
  it.each([
    ["no-auth", undefined, "cached_token"],
    ["unknown-model", undefined, "actual model identity"],
    ["unsupported-override", "chosen-model", "cannot be confirmed"],
    ["rejected-override", "chosen-model", "was not confirmed"],
    ["handshake-timeout", undefined, "handshake timeout"],
    ["protocol-error", undefined, "protocol failed (-32001)"],
  ])("refuses %s without inventing a successful model outcome", async (mode, override, message) => {
    const fixture = await negotiatedAgent(mode ?? "");
    try {
      await expect(
        new AcpTextProvider({ ...fixture.options, model: override }).generateStructured(task),
      ).rejects.toThrow(message);
      const prompts = fixture.messages.filter((entry) => entry.method === "session/prompt");
      expect(prompts).toHaveLength(
        ["unknown-model", "protocol-error"].includes(mode ?? "") ? 1 : 0,
      );
    } finally {
      await fixture.close();
    }
  });

  it.each(["confirmed-override", "updated-model"])(
    "records confirmed model and real usage for %s",
    async (mode) => {
      const fixture = await negotiatedAgent(mode);
      try {
        const result = await new AcpTextProvider({
          ...fixture.options,
          model: mode === "confirmed-override" ? "chosen-model" : undefined,
        }).generateStructured(task);
        expect(result).toMatchObject({
          model: mode === "confirmed-override" ? "chosen-model" : "actual-model",
          promptTokens: 12,
          completionTokens: 4,
          content: { chapter_markdown: "Draft" },
        });
        expect(fixture.messages.filter((entry) => entry.method === "session/prompt")).toHaveLength(
          1,
        );
      } finally {
        await fixture.close();
      }
    },
  );

  it.each(["not-a-url", "https://localhost/acp", "ws://user:password@localhost/acp"])(
    "rejects unsafe transport configuration: %s",
    (proxyUrl) => {
      expect(() => new AcpTextProvider({ proxyUrl, command: "fake", args: [] })).toThrow();
    },
  );

  it.each(["missing-config", "missing-token", "empty-token"])(
    "rejects %s before sending a prompt",
    async (mode) => {
      const fixture = await fakeAcp(() => {});
      try {
        if (mode === "empty-token") await writeFile(fixture.options.tokenFile ?? "", " \n");
        const provider = new AcpTextProvider({
          ...fixture.options,
          tokenFile:
            mode === "missing-config"
              ? undefined
              : mode === "missing-token"
                ? join(fixture.options.workspaceRoot ?? "", "absent-key")
                : fixture.options.tokenFile,
        });
        await expect(provider.generateStructured(task)).rejects.toThrow(
          mode === "missing-config"
            ? "requires"
            : mode === "missing-token"
              ? "unavailable"
              : "empty",
        );
        expect(fixture.messages).toHaveLength(0);
      } finally {
        await fixture.close();
      }
    },
  );

  it("expires a submitted silent turn, retains uncertainty and never retries", async () => {
    const fixture = await fakeAcp(() => {});
    const evidence = { operation_id: "timeout", external_effects: [], outcome_unknown: false };
    try {
      await expect(
        new AcpTextProvider({ ...fixture.options, executionMs: 40 }).generateStructured(task, {
          agentExecution: evidence,
        }),
      ).rejects.toThrow("timeout");
      expect(evidence.outcome_unknown).toBe(true);
      expect(fixture.messages.filter((entry) => entry.method === "session/prompt")).toHaveLength(1);
    } finally {
      await fixture.close();
    }
  });

  it("overall timeout still bounds an unanswered permission while execution is paused", async () => {
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
        new AcpTextProvider({
          ...fixture.options,
          executionMs: 1000,
          overallMs: 100,
        }).generateStructured(task, { requestPermission: () => new Promise(() => {}) }),
      ).rejects.toThrow("overall timeout");
      expect(fixture.messages.filter((entry) => entry.method === "session/prompt")).toHaveLength(1);
    } finally {
      await fixture.close();
    }
  });

  it("stream failure cannot emit success even after one valid body delta", async () => {
    const fixture = await fakeAcp((socket, message) => {
      textChunk(socket, '{"chapter_markdown":"Partial draft"}');
      stop(socket, message.id, "max_tokens");
    });
    const deltas: string[] = [];
    const outcomes: unknown[] = [];
    try {
      await expect(
        (async () => {
          for await (const delta of new AcpTextProvider(
            fixture.options,
          ).generateStructuredStreaming(task, { onOutcome: (outcome) => outcomes.push(outcome) }))
            deltas.push(delta);
        })(),
      ).rejects.toThrow("max_tokens");
      expect(deltas.join("")).toBe("Partial draft");
      expect(outcomes).toEqual([]);
    } finally {
      await fixture.close();
    }
  });

  it("rejects streaming review tasks before opening any transport", async () => {
    const fixture = await fakeAcp(() => {});
    try {
      const stream = new AcpTextProvider(fixture.options).generateStructuredStreaming({
        ...task,
        step: "editorial_review",
      });
      await expect(stream.next()).rejects.toThrow("chapter step");
      expect(fixture.messages).toHaveLength(0);
    } finally {
      await fixture.close();
    }
  });
});
