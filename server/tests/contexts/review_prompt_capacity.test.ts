import { describe, expect, it } from "vitest";

import { buildReviewPrompt } from "../../src/contexts/studio/application/buildReviewPrompt.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../../src/contexts/studio/application/generation_capacity.js";
import type { ReviewSourceDocument } from "../../src/contexts/studio/application/ports/review_outcome_store.js";
import { GenerationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";

function chapter(contentMarkdown: string): ReviewSourceDocument {
  return {
    documentId: "chapter-1",
    revisionId: "revision-1",
    kind: "chapter",
    title: "Saved chapter",
    contentMarkdown,
    metadataJson: '{"private":"unrelated metadata"}',
    position: 20,
  };
}

function promptBytes(documents: readonly ReviewSourceDocument[]): number {
  const prompt = buildReviewPrompt(documents);
  return Buffer.byteLength(prompt.systemPrompt) + Buffer.byteLength(prompt.userPrompt);
}

function contentBudget(): number {
  return GENERATION_PROMPT_BYTE_LIMIT - promptBytes([chapter("")]);
}

describe("complete review prompt byte budget", () => {
  it("admits the exact inclusive boundary and refuses the next UTF-8 byte", () => {
    const content = "x".repeat(contentBudget());
    expect(promptBytes([chapter(content)])).toBe(GENERATION_PROMPT_BYTE_LIMIT);
    expect(() => buildReviewPrompt([chapter(`${content}x`)])).toThrow(
      GenerationCapacityExceededError,
    );
  });

  it("counts Chinese UTF-8 bytes and saturates a multibyte excess at limit plus one", () => {
    const budget = contentBudget();
    const content = "界".repeat(Math.floor(budget / 3)) + "x".repeat(budget % 3);
    expect(content.length).toBeLessThan(budget);
    expect(promptBytes([chapter(content)])).toBe(GENERATION_PROMPT_BYTE_LIMIT);
    expect(() => buildReviewPrompt([chapter(`${content}界`)])).toThrowError(
      expect.objectContaining({
        resource: "prompt_bytes",
        limit: GENERATION_PROMPT_BYTE_LIMIT,
        observed: GENERATION_PROMPT_BYTE_LIMIT + 1,
      }),
    );
  });

  it("counts escaping and every chapter delimiter before joining the final prompt", () => {
    const fragment = '["quoted"]\\';
    const emptyBytes = promptBytes([chapter("")]);
    const escapedBytes = promptBytes([chapter(fragment)]);
    expect(escapedBytes - emptyBytes).toBeGreaterThan(Buffer.byteLength(fragment));
    const content = "x".repeat(contentBudget() - (escapedBytes - emptyBytes)) + fragment;
    expect(promptBytes([chapter(content)])).toBe(GENERATION_PROMPT_BYTE_LIMIT);
    expect(() =>
      buildReviewPrompt([chapter(content), { ...chapter(""), documentId: "second" }]),
    ).toThrow(GenerationCapacityExceededError);
  });

  it("skips non-chapter bodies even if they exceed the prompt budget", () => {
    const unrelated = { ...chapter("x".repeat(GENERATION_PROMPT_BYTE_LIMIT + 1)), kind: "world" };
    expect(buildReviewPrompt([unrelated])).toEqual(buildReviewPrompt([]));
  });

  it("preserves captured cross-volume order instead of sorting local chapter positions", () => {
    const prompt = buildReviewPrompt([
      { ...chapter("First volume tail."), documentId: "captured-first", position: 20 },
      { ...chapter("Second volume start."), documentId: "captured-second", position: 1 },
    ]).userPrompt;
    expect(prompt.indexOf("captured-first")).toBeLessThan(prompt.indexOf("captured-second"));
  });
});
