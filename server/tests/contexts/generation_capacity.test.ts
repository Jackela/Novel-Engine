import { describe, expect, it } from "vitest";

import {
  BoundedPromptWriter,
  GENERATION_PROMPT_BYTE_LIMIT,
} from "../../src/contexts/studio/application/generation_capacity.js";
import type { ProposalContextSource } from "../../src/contexts/studio/application/ports/proposal_context_store.js";
import type {
  DocumentWithCurrent,
  RevisionRecord,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  buildProposalTask,
  SYSTEM_PROMPT,
} from "../../src/contexts/studio/application/proposal_landing.js";
import { GenerationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";

function proposalFixture(contentMarkdown: string): {
  readonly context: ProposalContextSource;
} {
  const now = new Date("2026-09-03T00:00:00.000Z");
  const revision: RevisionRecord = {
    id: "revision-1",
    documentId: "document-1",
    parentRevisionId: null,
    revisionNumber: 1,
    contentMarkdown,
    metadataJson: "{}",
    source: "author",
    wordCount: 0,
    createdAt: now,
  };
  const document: DocumentWithCurrent = {
    id: "document-1",
    projectId: "project-1",
    kind: "chapter",
    title: "Chapter 1",
    position: 1,
    volumeId: null,
    beatRef: null,
    loreAliasesJson: "[]",
    loreStatus: "draft",
    currentRevisionId: revision.id,
    createdAt: now,
    updatedAt: now,
    currentRevision: revision,
  };
  return {
    context: {
      projectId: "project-1",
      target: document,
      documents: [document],
      volumes: [],
    },
  };
}

function buildTask(contentMarkdown: string) {
  const fixture = proposalFixture(contentMarkdown);
  return buildProposalTask("chapter_revision", "continue", "", fixture.context);
}

describe("generation prompt capacity policy", () => {
  it("accepts exactly 8 MiB including UTF-8 text and separators", () => {
    const writer = new BoundedPromptWriter("系");
    writer.writeLine("🙂");
    writer.writeLine("a".repeat(GENERATION_PROMPT_BYTE_LIMIT - 3 - 4 - 1));

    expect(Buffer.byteLength(writer.finish())).toBe(GENERATION_PROMPT_BYTE_LIMIT - 3);
  });

  it("refuses plus one without retaining the crossing fragment", () => {
    const writer = new BoundedPromptWriter("system");
    writer.writeLine("kept");
    const retained = writer.finish();

    expect(() => writer.writeLine("界".repeat(GENERATION_PROMPT_BYTE_LIMIT))).toThrowError(
      expect.objectContaining({
        code: "GENERATION_CAPACITY_EXCEEDED",
        resource: "prompt_bytes",
        limit: GENERATION_PROMPT_BYTE_LIMIT,
        observed: GENERATION_PROMPT_BYTE_LIMIT + 1,
      }),
    );
    expect(writer.finish()).toBe(retained);
  });

  it("validates safe excess evidence and saturates observations", () => {
    expect(
      new GenerationCapacityExceededError(
        "prompt_bytes",
        GENERATION_PROMPT_BYTE_LIMIT,
        Number.MAX_SAFE_INTEGER,
      ),
    ).toMatchObject({
      message: "Generation capacity exceeded.",
      observed: GENERATION_PROMPT_BYTE_LIMIT + 1,
    });
    expect(
      () =>
        new GenerationCapacityExceededError(
          "prompt_bytes",
          GENERATION_PROMPT_BYTE_LIMIT,
          GENERATION_PROMPT_BYTE_LIMIT,
        ),
    ).toThrow(RangeError);
  });

  it.each([
    [Number.NaN, GENERATION_PROMPT_BYTE_LIMIT + 1],
    [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER],
    [GENERATION_PROMPT_BYTE_LIMIT, Number.POSITIVE_INFINITY],
    [GENERATION_PROMPT_BYTE_LIMIT, GENERATION_PROMPT_BYTE_LIMIT + 0.5],
  ])("rejects unsafe capacity evidence %#", (limit, observed) => {
    expect(() => new GenerationCapacityExceededError("prompt_bytes", limit, observed)).toThrow(
      RangeError,
    );
  });

  it("admits an exact complete task and refuses one additional manuscript byte", () => {
    const empty = buildTask("");
    const fixedBytes = Buffer.byteLength(empty.systemPrompt) + Buffer.byteLength(empty.userPrompt);
    const exactContent = "a".repeat(GENERATION_PROMPT_BYTE_LIMIT - fixedBytes);
    const exact = buildTask(exactContent);

    expect(Buffer.byteLength(exact.systemPrompt) + Buffer.byteLength(exact.userPrompt)).toBe(
      GENERATION_PROMPT_BYTE_LIMIT,
    );
    expect(() => buildTask(`${exactContent}a`)).toThrow(GenerationCapacityExceededError);
    expect(exact.systemPrompt).toBe(SYSTEM_PROMPT);
  });
});
