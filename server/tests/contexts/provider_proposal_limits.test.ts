import { describe, expect, it } from "vitest";

import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { validatedProposalOrThrow } from "../../src/contexts/studio/application/proposal_landing.js";

describe("proposal markdown semantic boundary", () => {
  it("accepts exactly 1,000,000 Unicode code points", () => {
    const prefix = "# Chapter\n";
    const exact = `${prefix}${"x".repeat(1_000_000 - prefix.length)}`;

    expect(validatedProposalOrThrow({ content: { chapter_markdown: exact } }).proposal).toBe(exact);
  });

  it("rejects provider output above 1,000,000 Unicode code points", () => {
    const prefix = "# Chapter\n";
    const oversized = `${prefix}${"x".repeat(1_000_001 - prefix.length)}`;

    expect(() => validatedProposalOrThrow({ content: { chapter_markdown: oversized } })).toThrow(
      TextGenerationProviderError,
    );
    expect(() => validatedProposalOrThrow({ content: { chapter_markdown: oversized } })).toThrow(
      /exceeds 1,000,000 Unicode code point limit/,
    );
  });

  it("counts an astral emoji as one Unicode code point instead of two UTF-16 units", () => {
    const safe = `# Chapter\n${"😀".repeat(600_000)}`;
    const oversized = `# Chapter\n${"😀".repeat(1_000_000)}`;

    expect(() => validatedProposalOrThrow({ content: { chapter_markdown: safe } })).not.toThrow();
    expect(() => validatedProposalOrThrow({ content: { chapter_markdown: oversized } })).toThrow(
      /exceeds 1,000,000 Unicode code point limit/,
    );
  });
});
