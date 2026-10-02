import { describe, expect, it } from "vitest";

import type { TextGenerationTask } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DeterministicStoryProvider } from "../../src/contexts/ai/infrastructure/providers/deterministic_story_provider.js";

/**
 * DR-023: the deterministic (mock) provider is no longer English-only — a zh
 * task produces Chinese prose, Chinese review findings, and Chinese placeholders
 * while every en task keeps the byte-identical English output.
 */

function chapterTask(step: string, overrides: Record<string, unknown> = {}): TextGenerationTask {
  return {
    step,
    systemPrompt: "system",
    userPrompt: "user",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2, title: "The Crossing", ...overrides },
  };
}

function proseBody(markdown: string | undefined): string {
  expect(markdown, "expected chapter_markdown prose").toBeDefined();
  return markdown as string;
}

describe("deterministic story provider writing language (DR-023)", () => {
  const provider = new DeterministicStoryProvider();

  it("produces Chinese prose for a zh chapter_draft that still reflects the task", async () => {
    const result = await provider.generateStructured({
      ...chapterTask("chapter_draft"),
      language: "zh",
    });
    const prose = proseBody(result.content.chapter_markdown as string | undefined);

    expect(prose.length).toBeGreaterThan(400);
    expect(prose).toContain("第2章");
    expect(prose).toContain("The Crossing");
    expect(prose).toMatch(/[\u3400-\u9fff]/u);
    expect(prose).not.toContain("Chapter 2:");
  });

  it("produces a distinct Chinese revision that still reflects the task", async () => {
    const draft = proseBody(
      (await provider.generateStructured({ ...chapterTask("chapter_draft"), language: "zh" }))
        .content.chapter_markdown as string | undefined,
    );
    const revision = proseBody(
      (await provider.generateStructured({ ...chapterTask("chapter_revision"), language: "zh" }))
        .content.chapter_markdown as string | undefined,
    );

    expect(revision).not.toBe(draft);
    expect(revision).toContain("第2章");
    expect(revision).toContain("The Crossing");
    expect(revision).toMatch(/[\u3400-\u9fff]/u);
  });

  it("treats an absent language as English and keeps the English prose", async () => {
    const implicit = await provider.generateStructured(chapterTask("chapter_draft"));
    const explicit = await provider.generateStructured({
      ...chapterTask("chapter_draft"),
      language: "en",
    });

    expect(implicit.content.chapter_markdown).toBe(explicit.content.chapter_markdown);
    expect(String(implicit.content.chapter_markdown)).toContain("Chapter 2");
  });

  it("streams joined Chinese deltas byte-identically to the synchronous prose", async () => {
    const task = { ...chapterTask("chapter_revision"), language: "zh" as const };
    const deltas: string[] = [];
    const stream = provider.generateStructuredStreaming?.(task);
    if (stream === undefined) throw new Error("the mock provider must support streaming");
    for await (const delta of stream) deltas.push(delta);

    expect(deltas.length).toBeGreaterThan(1);
    const sync = proseBody(
      (await provider.generateStructured(task)).content.chapter_markdown as string | undefined,
    );
    expect(deltas.join("")).toBe(sync);
  });

  it("produces Chinese review findings and lore placeholders for zh tasks", async () => {
    const review = await provider.generateStructured({
      ...chapterTask("editorial_review"),
      language: "zh",
      metadata: {
        documents: [
          { id: "doc-1", title: "第一章 初雪", words: 10, empty: false, thin_below: 250 },
        ],
      },
    });
    const findings = (review.content as { findings: Array<{ message: string }> }).findings;
    expect(findings[0]?.message).toContain("第一章 初雪");
    expect(findings[0]?.message).toMatch(/[\u3400-\u9fff]/u);

    const lore = await provider.generateStructured({
      ...chapterTask("lore_extract"),
      language: "zh",
    });
    const candidates = (lore.content as { candidates: Array<{ title: string; summary: string }> })
      .candidates;
    expect(candidates.map((candidate) => candidate.title)).toEqual(["占位角色", "占位世界"]);
    for (const candidate of candidates) {
      expect(candidate.summary).toMatch(/[\u3400-\u9fff]/u);
    }
  });
});
