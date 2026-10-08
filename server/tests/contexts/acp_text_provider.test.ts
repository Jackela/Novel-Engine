import { describe, expect, it } from "vitest";
import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { fakeAcp, stop, textChunk } from "./acp_provider_fixture.js";

const task: TextGenerationTask = {
  step: "chapter_draft",
  systemPrompt: "Write a chapter",
  userPrompt: "Snow",
  responseSchema: { chapter_markdown: "string" },
  metadata: {},
};

describe("ACP provider over its real WebSocket boundary", () => {
  it("authenticates cached CLI credentials, records actual session model and unwraps live Chinese deltas", async () => {
    const fixture = await fakeAcp((socket, message) => {
      textChunk(socket, '{"chapter_markdown":"雪');
      textChunk(socket, '夜\\n来客"}');
      stop(socket, message.id);
    });
    try {
      const provider = new AcpTextProvider(fixture.options);
      const outcomes: unknown[] = [];
      const deltas: string[] = [];
      for await (const delta of provider.generateStructuredStreaming(task, {
        onOutcome: (outcome) => outcomes.push(outcome),
      }))
        deltas.push(delta);
      expect(deltas).toEqual(["雪", "夜\n来客"]);
      expect(outcomes).toEqual([
        { model: "fake-model", promptTokens: null, completionTokens: null },
      ]);
      expect(
        fixture.messages.filter((message) => message.method === "session/prompt"),
      ).toHaveLength(1);
      expect(fixture.messages.find((message) => message.method === "authenticate")?.params).toEqual(
        { methodId: "cached_token" },
      );
    } finally {
      await fixture.close();
    }
  });
  it.each(["max_tokens", "refusal", "cancelled"])(
    "refuses %s even if the JSON body looks complete",
    async (reason) => {
      const fixture = await fakeAcp((socket, message) => {
        textChunk(socket, '{"chapter_markdown":"Draft"}');
        stop(socket, message.id, reason);
      });
      try {
        await expect(
          new AcpTextProvider(fixture.options).generateStructured(task),
        ).rejects.toThrow();
        expect(
          fixture.messages.filter((message) => message.method === "session/prompt"),
        ).toHaveLength(1);
      } finally {
        await fixture.close();
      }
    },
  );
  it("requires a live permission channel and never replays a submitted prompt with side effects", async () => {
    const fixture = await fakeAcp((socket) => {
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 900,
          method: "session/request_permission",
          params: {
            sessionId: "session-1",
            toolCall: { toolCallId: "tool-1", title: "Write material", kind: "edit" },
            options: [{ optionId: "allow", name: "Allow", kind: "allow_once" }],
          },
        }),
      );
    });
    try {
      await expect(new AcpTextProvider(fixture.options).generateStructured(task)).rejects.toThrow(
        "interaction channel",
      );
      expect(
        fixture.messages.filter((message) => message.method === "session/prompt"),
      ).toHaveLength(1);
    } finally {
      await fixture.close();
    }
  });
  it("cancels a silent prompt and tears down the transport", async () => {
    const fixture = await fakeAcp(() => {});
    try {
      const abort = new AbortController();
      const pending = new AcpTextProvider(fixture.options).generateStructured(task, {
        signal: abort.signal,
      });
      setTimeout(() => abort.abort(), 50);
      await expect(pending).rejects.toThrow("cancelled");
    } finally {
      await fixture.close();
    }
  });
  it("rejects EOF after a completed tool without retrying or erasing uncertain evidence", async () => {
    const fixture = await fakeAcp((socket) => socket.close());
    const evidence = { operation_id: "op", external_effects: [], outcome_unknown: false };
    try {
      await expect(
        new AcpTextProvider(fixture.options).generateStructured(task, { agentExecution: evidence }),
      ).rejects.toThrow("closed");
      expect(evidence.outcome_unknown).toBe(true);
      expect(
        fixture.messages.filter((message) => message.method === "session/prompt"),
      ).toHaveLength(1);
    } finally {
      await fixture.close();
    }
  });
  it("pauses the execution budget while the user considers a permission decision", async () => {
    const fixture = await fakeAcp((socket, message) => {
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 900,
          method: "session/request_permission",
          params: {
            sessionId: "session-1",
            toolCall: { toolCallId: "tool-1", title: "Material read", kind: "read" },
            options: [{ optionId: "allow", name: "Allow", kind: "allow_once" }],
          },
        }),
      );
      const onDecision = (bytes: Buffer) => {
        const response = JSON.parse(bytes.toString());
        if (response.id !== 900 || response.result === undefined) return;
        socket.off("message", onDecision);
        textChunk(socket, '{"chapter_markdown":"Draft"}');
        stop(socket, message.id);
      };
      socket.on("message", onDecision);
    });
    try {
      const result = await new AcpTextProvider({
        ...fixture.options,
        executionMs: 20,
      }).generateStructured(task, {
        requestPermission: () => new Promise((resolve) => setTimeout(() => resolve("allow"), 60)),
      });
      expect(result.content).toEqual({ chapter_markdown: "Draft" });
    } finally {
      await fixture.close();
    }
  });
});
