import { describe, expect, it } from "vitest";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { fakeAcp, stop, textChunk } from "./acp_provider_fixture.js";

describe("ACP task language across both prompt channels", () => {
  it.each(["zh", "en"] as const)(
    "carries %s into the session and submitted review prompt",
    async (language) => {
      const fixture = await fakeAcp((socket, request) => {
        textChunk(socket, '{"findings":[]}');
        stop(socket, request.id);
      });
      try {
        await new AcpTextProvider(fixture.options).generateStructured({
          step: "editorial_review",
          language,
          systemPrompt: "Review the captured manuscript.",
          userPrompt: "An untrusted chapter snapshot.",
          responseSchema: { findings: [] },
          metadata: {},
        });
        const session = fixture.messages.find((entry) => entry.method === "session/new");
        const prompt = fixture.messages.find((entry) => entry.method === "session/prompt");
        const expected = language === "zh" ? "in Chinese" : "in English";
        expect(JSON.stringify(session?.params)).toContain(expected);
        expect(JSON.stringify(prompt?.params)).toContain(expected);
        expect(JSON.stringify(prompt?.params)).toContain("Preserve JSON field names");
      } finally {
        await fixture.close();
      }
    },
  );
});
