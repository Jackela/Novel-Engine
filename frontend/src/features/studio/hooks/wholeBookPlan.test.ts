import { describe, expect, it } from "vitest";

import { chapter, project, volume } from "@/test/factories";

import { needsGeneration, readingOrderChapters, wholeBookPlan } from "./wholeBookPlan";

// Local thin wrapper keeping the input-object call style and the
// `Chapter <id>` default title these specs assert on.
function fixture(input: Partial<Parameters<typeof chapter>[1]> & { id: string }) {
  return chapter(input.id, { title: `Chapter ${input.id}`, ...input });
}

const baseProject = project();

describe("needsGeneration (#318 candidate rule)", () => {
  it("treats every revision source except the accepted AI one as a candidate", () => {
    expect(needsGeneration(fixture({ id: "a", revision_source: "author" }))).toBe(true);
    expect(needsGeneration(fixture({ id: "b", revision_source: "restore" }))).toBe(true);
    expect(needsGeneration(fixture({ id: "c", revision_source: "ai-accepted" }))).toBe(false);
  });
});

describe("readingOrderChapters (ADR-0005)", () => {
  it("orders by volume position first, then in-volume chapter position", () => {
    const project = {
      ...baseProject,
      volumes: [volume("volume-2", 1), volume("volume-1", 0)],
      documents: [
        fixture({ id: "late", volume_id: "volume-2", position: 1 }),
        fixture({ id: "first-b", volume_id: "volume-1", position: 1 }),
        fixture({ id: "first-a", volume_id: "volume-1", position: 0 }),
        fixture({
          id: "outline-doc",
          kind: "outline",
          volume_id: null,
          position: 99,
        }),
        fixture({ id: "late-a", volume_id: "volume-2", position: 0 }),
      ],
    };
    expect(readingOrderChapters(project).map((document) => document.id)).toEqual([
      "first-a",
      "first-b",
      "late-a",
      "late",
    ]);
  });

  it("falls back to the first volume for chapters without a link", () => {
    const project = {
      ...baseProject,
      volumes: [volume("volume-late", 1), volume("volume-first", 0)],
      documents: [
        fixture({ id: "linked", volume_id: "volume-late", position: 0 }),
        fixture({ id: "unlinked", volume_id: null, position: 50 }),
      ],
    };
    expect(readingOrderChapters(project).map((document) => document.id)).toEqual([
      "unlinked",
      "linked",
    ]);
  });

  it("does not mutate the project document list", () => {
    const documents = [fixture({ id: "b", position: 1 }), fixture({ id: "a", position: 0 })];
    const project = { ...baseProject, documents };
    readingOrderChapters(project);
    expect(documents.map((document) => document.id)).toEqual(["b", "a"]);
  });
});

describe("wholeBookPlan", () => {
  it("skips accepted AI revisions and keeps reading order", () => {
    const project = {
      ...baseProject,
      volumes: [volume("volume-1", 0)],
      documents: [
        fixture({ id: "one", position: 0 }),
        fixture({ id: "two", position: 1, revision_source: "ai-accepted" }),
        fixture({ id: "three", position: 2 }),
      ],
    };
    expect(wholeBookPlan(project).chapters).toEqual([
      { id: "one", title: "Chapter one", requiresConfirmation: false },
      { id: "three", title: "Chapter three", requiresConfirmation: false },
    ]);
  });

  it("is empty when every chapter already carries an accepted AI revision", () => {
    const project = {
      ...baseProject,
      volumes: [volume("volume-1", 0)],
      documents: [fixture({ id: "one", revision_source: "ai-accepted" })],
    };
    expect(wholeBookPlan(project).chapters).toEqual([]);
    expect(wholeBookPlan(project).safe).toEqual([]);
    expect(wholeBookPlan(project).confirmation).toEqual([]);
  });
});

describe("wholeBookPlan split (#DR-007)", () => {
  it("separates empty chapters from chapters holding non-AI text", () => {
    const project = {
      ...baseProject,
      volumes: [volume("volume-1", 0)],
      documents: [
        fixture({ id: "empty", position: 0 }),
        fixture({ id: "hand", position: 1, content_markdown: "Hand-written.", word_count: 2 }),
        fixture({ id: "accepted", position: 2, revision_source: "ai-accepted", word_count: 9 }),
      ],
    };

    expect(wholeBookPlan(project).safe).toEqual([
      { id: "empty", title: "Chapter empty", requiresConfirmation: false },
    ]);
    expect(wholeBookPlan(project).confirmation).toEqual([
      { id: "hand", title: "Chapter hand", requiresConfirmation: true },
    ]);
  });
});
