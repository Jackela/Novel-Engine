import { describe, expect, it } from "vitest";
import { AcpTextProvider } from "../../src/contexts/ai/infrastructure/providers/AcpTextProvider.js";
import { fakeAcp } from "./acp_provider_fixture.js";

describe("ACP transport prompt admission", () => {
  it("refuses an oversized encoded prompt before initialization or model/tool execution", async () => {
    const fixture = await fakeAcp(() => {
      throw new Error("Oversized prompt must never reach the agent");
    });
    try {
      await expect(
        new AcpTextProvider(fixture.options).generateStructured({
          step: "editorial_review",
          language: "zh",
          systemPrompt: "Review captured chapters.",
          userPrompt: "文".repeat(400_000),
          responseSchema: { findings: [] },
          metadata: {},
        }),
      ).rejects.toThrow("1 MiB transport budget");
      expect(fixture.messages).toEqual([]);
    } finally {
      await fixture.close();
    }
  });
});
