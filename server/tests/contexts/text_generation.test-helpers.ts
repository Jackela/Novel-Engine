import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";

/** The shared task fixture for provider tests (chapter 2, "The Crossing"). */
export function chapterTask(
  step: string,
  overrides: Record<string, unknown> = {},
): TextGenerationTask {
  return {
    step,
    systemPrompt: "system",
    userPrompt: "user",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2, title: "The Crossing", ...overrides },
  };
}

/** A credential shaped like the real ones, unique per provider. */
export function testCredential(provider: string): string {
  return ["test", provider, "credential"].join("-");
}
