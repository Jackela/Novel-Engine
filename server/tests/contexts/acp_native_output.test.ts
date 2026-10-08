import { describe, expect, it } from "vitest";
import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { fakeAcp, stop, textChunk } from "./acp_provider_fixture.js";

const task: TextGenerationTask = {
  step: "chapter_draft",
  systemPrompt: "Only JSON",
  userPrompt: "Snow",
  responseSchema: { chapter_markdown: { type: "string" } },
  metadata: {},
};

describe("native ACP commentary before final structured output", () => {
  it("filters bounded commentary across chunks while yielding real chapter deltas before end_turn", async () => {
    let ended = false;
    const fixture = await fakeAcp((socket, message) => {
      textChunk(socket, "I'll read the material first. The external file was blocked.\n{");
      textChunk(socket, '"chapter_mark');
      textChunk(socket, 'down":"雪夜');
      setTimeout(() => {
        ended = true;
        textChunk(socket, '来客"}');
        stop(socket, message.id);
      }, 50);
    });
    try {
      const stream = new AcpTextProvider(fixture.options).generateStructuredStreaming(task);
      expect(await stream.next()).toEqual({ done: false, value: "雪夜" });
      expect(ended).toBe(false);
      expect(await stream.next()).toEqual({ done: false, value: "来客" });
      expect((await stream.next()).done).toBe(true);
    } finally {
      await fixture.close();
    }
  });
  it.each([
    '{"chapter_markdown":"Draft"}{"chapter_markdown":"Extra"}',
    '{"chapter_markdown":"Draft"} afterword',
    "Plain prose without JSON",
  ])("refuses extra objects, trailing prose or missing structured output", async (text) => {
    const fixture = await fakeAcp((socket, message) => {
      textChunk(socket, text);
      stop(socket, message.id);
    });
    try {
      await expect(new AcpTextProvider(fixture.options).generateStructured(task)).rejects.toThrow();
    } finally {
      await fixture.close();
    }
  });
});
