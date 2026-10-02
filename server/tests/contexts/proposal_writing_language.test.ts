import { describe, expect, it } from "vitest";
import { buildLoreExtractTask } from "../../src/contexts/studio/application/lore_extract_task.js";
import type {
  DocumentWithCurrent,
  RevisionRecord,
} from "../../src/contexts/studio/application/ports/document_store.js";
import type { ProposalContextSource } from "../../src/contexts/studio/application/ports/proposal_context_store.js";
import {
  buildProposalTask,
  SYSTEM_PROMPT,
  SYSTEM_PROMPT_ZH,
} from "../../src/contexts/studio/application/proposal_landing.js";
import { inferWritingLanguage } from "../../src/contexts/studio/application/writing_language.js";

/**
 * DR-023: the project-scoped writing language is inferred from the captured
 * project text and carried through the provider task into the proposal
 * system prompt. zh projects ask for Chinese prose; en projects keep the
 * English prompt byte-for-byte.
 */

const NOW = new Date("2026-10-01T00:00:00.000Z");

const CHINESE_CHAPTER = [
  "她推开门时，雨声灌满了整条走廊。灯在风里摇晃，像有人举着它犹豫不决。",
  "远处传来钟声，一下又一下，把夜色敲得更薄。她把信折好，放进外套的内袋。",
].join("\n\n");

const ENGLISH_CHAPTER = [
  "She pushed the door open and rain filled the corridor, one lamp swinging above the stairs.",
  "Somewhere below, a bell counted the hour twice, as if unsure of the count.",
].join("\n\n");

function documentFixture(input: {
  id: string;
  kind: string;
  title: string;
  contentMarkdown: string;
}): DocumentWithCurrent {
  const revision: RevisionRecord = {
    id: `${input.id}-revision`,
    documentId: input.id,
    parentRevisionId: null,
    revisionNumber: 1,
    contentMarkdown: input.contentMarkdown,
    metadataJson: "{}",
    source: "author",
    wordCount: 0,
    createdAt: NOW,
  };
  return {
    id: input.id,
    projectId: "project-1",
    kind: input.kind,
    title: input.title,
    position: 1,
    volumeId: null,
    beatRef: null,
    loreAliasesJson: "[]",
    loreStatus: "draft",
    currentRevisionId: revision.id,
    createdAt: NOW,
    updatedAt: NOW,
    currentRevision: revision,
  };
}

/** A captured project whose target chapter and optional outline decide the language. */
function capturedProject(input: {
  chapterTitle: string;
  chapterMarkdown: string;
  outlineMarkdown?: string;
}): ProposalContextSource {
  const target = documentFixture({
    id: "chapter-target",
    kind: "chapter",
    title: input.chapterTitle,
    contentMarkdown: input.chapterMarkdown,
  });
  const documents: DocumentWithCurrent[] = [target];
  if (input.outlineMarkdown !== undefined) {
    documents.unshift(
      documentFixture({
        id: "outline-1",
        kind: "outline",
        title: "大纲",
        contentMarkdown: input.outlineMarkdown,
      }),
    );
  }
  return { projectId: "project-1", target, documents, volumes: [] };
}

describe("project writing language inference (DR-023)", () => {
  it("infers Chinese when Han characters carry the script mass", () => {
    expect(inferWritingLanguage([CHINESE_CHAPTER, "第一章 初雪"])).toBe("zh");
  });

  it("infers English when Latin letters dominate", () => {
    expect(inferWritingLanguage([ENGLISH_CHAPTER, "Chapter 1"])).toBe("en");
  });

  it("defaults to English without any project text", () => {
    expect(inferWritingLanguage([])).toBe("en");
    expect(inferWritingLanguage(["", "   "])).toBe("en");
  });

  it("keeps English for an English chapter with a stray Han phrase", () => {
    expect(inferWritingLanguage([`${ENGLISH_CHAPTER}\n\n她在远处挥手。`])).toBe("en");
  });
});

describe("proposal prompt language (DR-023)", () => {
  it("carries zh into the system prompt for a Chinese project", () => {
    const task = buildProposalTask(
      "chapter_draft",
      "generate",
      "",
      capturedProject({ chapterTitle: "第一章 初雪", chapterMarkdown: CHINESE_CHAPTER }),
    );

    expect(task.language).toBe("zh");
    expect(task.systemPrompt).toBe(SYSTEM_PROMPT_ZH);
    expect(task.systemPrompt).toContain("简体中文");
    expect(task.systemPrompt).not.toBe(SYSTEM_PROMPT);
  });

  it("keeps the English system prompt for an English project", () => {
    const task = buildProposalTask(
      "chapter_revision",
      "continue",
      "",
      capturedProject({ chapterTitle: "Chapter 1", chapterMarkdown: ENGLISH_CHAPTER }),
    );

    expect(task.language).toBe("en");
    expect(task.systemPrompt).toBe(SYSTEM_PROMPT);
    expect(task.systemPrompt).toContain("English");
  });

  it("infers the writing language from the outline when the target chapter is empty", () => {
    const task = buildProposalTask(
      "chapter_draft",
      "generate",
      "",
      capturedProject({
        chapterTitle: "Chapter 2",
        chapterMarkdown: "# Chapter 2\n\n",
        outlineMarkdown: "# 大纲\n\n第一章：初雪\n第二章：旧债\n第三章：归途",
      }),
    );

    expect(task.language).toBe("zh");
    expect(task.systemPrompt).toBe(SYSTEM_PROMPT_ZH);
  });
});

describe("lore extraction language (DR-023)", () => {
  it("marks a Chinese segment as Chinese and an English segment as English", () => {
    expect(buildLoreExtractTask("她推开档案馆的门，灰尘在光柱里翻滚。").language).toBe("zh");
    expect(buildLoreExtractTask("Mira met Tomas at the flood market.").language).toBe("en");
  });
});
