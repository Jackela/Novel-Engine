/**
 * Direct contract tests for BeatAssociationService (#313, DR-043): a chapter
 * links to at most one beat of its project's outline document; the stored
 * reference is the heading title and every read resolves it against the live
 * outline, degrading a renamed or removed heading to unlinked without an
 * error. Store command fakes record through the port, so the write payload,
 * the authority selection rule, and the refusal messages are pinned here.
 */
import { describe, expect, it } from "vitest";

import { BeatAssociationService } from "../../src/contexts/studio/application/beat_association_service.js";
import type {
  DocumentStore,
  DocumentWithCurrent,
  RevisionRecord,
} from "../../src/contexts/studio/application/ports/document_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};
const SCOPE: ProjectScope = { ownerId: "owner-1" };
const NOW = new Date("2026-09-03T00:00:00.000Z");

const OUTLINE_CONTENT = [
  "# Outline",
  "",
  "Working notes before the first beat.",
  "",
  "## The Storm",
  "",
  "Rain floods the harbour.",
  "",
  "### The Archive",
  "Mara decodes the chart.",
].join("\n");

function revisionFixture(contentMarkdown: string, id = "revision-1"): RevisionRecord {
  return {
    id,
    documentId: "outline-1",
    parentRevisionId: null,
    revisionNumber: 1,
    contentMarkdown,
    metadataJson: "{}",
    source: "author",
    wordCount: 0,
    createdAt: NOW,
  };
}

function documentFixture(overrides: Partial<DocumentWithCurrent> = {}): DocumentWithCurrent {
  const base: DocumentWithCurrent = {
    id: "chapter-1",
    projectId: "project-1",
    kind: "chapter",
    title: "Chapter One",
    position: 1,
    volumeId: "volume-1",
    beatRef: null,
    loreAliasesJson: "[]",
    loreStatus: "draft",
    currentRevisionId: "chapter-revision-1",
    createdAt: NOW,
    updatedAt: NOW,
    currentRevision: revisionFixture("Chapter body.", "chapter-revision-1"),
  };
  return { ...base, ...overrides };
}

function outlineDocument(content: string | null, id = "outline-1"): DocumentWithCurrent {
  return documentFixture({
    id,
    kind: "outline",
    title: "Outline",
    currentRevision: content === null ? null : revisionFixture(content, `${id}-revision`),
    currentRevisionId: content === null ? null : `${id}-revision`,
  });
}

type FakeStore = Pick<DocumentStore, "findDocuments" | "findDocument" | "setBeatReference">;
type BeatWrite = [ProjectScope, string, string, { beatRef: string | null; now: Date }];
type BatchRead = [ProjectScope, string];
type DocumentRead = [ProjectScope, string, string];

function harness(
  config: {
    documents?: DocumentWithCurrent[];
    documentFailure?: Error;
    writeFailure?: Error;
    writeResult?: DocumentWithCurrent;
  } = {},
) {
  const batchReads: BatchRead[] = [];
  const documentReads: DocumentRead[] = [];
  const writes: BeatWrite[] = [];
  let clockCalls = 0;
  const store: FakeStore = {
    findDocuments: (scope, projectId) => {
      batchReads.push([scope, projectId]);
      return config.documents ?? [];
    },
    findDocument: (scope, projectId, documentId) => {
      documentReads.push([scope, projectId, documentId]);
      if (config.documentFailure !== undefined) throw config.documentFailure;
      const found = (config.documents ?? []).find(
        (document) => document.id === documentId && document.projectId === projectId,
      );
      if (found === undefined) throw new NotFoundError(`Document not found: ${documentId}.`);
      return found;
    },
    setBeatReference: (scope, projectId, documentId, input) => {
      writes.push([scope, projectId, documentId, input]);
      if (config.writeFailure !== undefined) throw config.writeFailure;
      const updated = config.writeResult;
      if (updated === undefined) throw new Error("test must provide the write result");
      return updated;
    },
  };
  const service = new BeatAssociationService(store as unknown as DocumentStore, () => {
    clockCalls += 1;
    return NOW;
  });
  return { service, batchReads, documentReads, writes, clockCalls: () => clockCalls };
}

const OUTLINE_CANDIDATES = [{ title: "The Storm" }, { title: "The Archive" }];

describe("BeatAssociationService linking (#313)", () => {
  it("links the trimmed heading title and answers the live resolved view", () => {
    const chapter = documentFixture();
    const outline = outlineDocument(OUTLINE_CONTENT);
    const linked = documentFixture({ beatRef: "The Storm" });
    const { service, batchReads, writes, clockCalls } = harness({
      documents: [chapter, outline],
      writeResult: linked,
    });

    const payload = service.linkChapterBeat(PRINCIPAL, "project-1", "chapter-1", {
      beat: "  The Storm  ",
    });

    expect(writes).toEqual([[SCOPE, "project-1", "chapter-1", { beatRef: "The Storm", now: NOW }]]);
    expect(payload).toEqual({
      beat: { title: "The Storm", content: "Rain floods the harbour." },
      candidates: OUTLINE_CANDIDATES,
      outline: { document_id: "outline-1", title: "Outline", outline_count: 1 },
    });
    expect(batchReads).toEqual([[SCOPE, "project-1"]]);
    expect(clockCalls()).toBe(1);
  });

  it("clears the association with an explicit null and keeps serving the catalog", () => {
    const chapter = documentFixture({ beatRef: "The Storm" });
    const cleared = documentFixture();
    const { service, writes, clockCalls } = harness({
      documents: [chapter, outlineDocument(OUTLINE_CONTENT)],
      writeResult: cleared,
    });

    const payload = service.linkChapterBeat(PRINCIPAL, "project-1", "chapter-1", { beat: null });

    expect(writes[0]?.[3]).toEqual({ beatRef: null, now: NOW });
    expect(payload).toEqual({
      beat: null,
      candidates: OUTLINE_CANDIDATES,
      outline: { document_id: "outline-1", title: "Outline", outline_count: 1 },
    });
    expect(clockCalls()).toBe(1);
  });

  it("refuses a blank beat title before any store read or clock reading", () => {
    const { service, batchReads, writes, clockCalls } = harness({
      documents: [documentFixture(), outlineDocument(OUTLINE_CONTENT)],
    });
    for (const beat of ["", "   ", "\t"]) {
      expect(() => service.linkChapterBeat(PRINCIPAL, "project-1", "chapter-1", { beat })).toThrow(
        new InvalidOperationError("An outline beat title is required to link a chapter."),
      );
    }
    expect(batchReads).toEqual([]);
    expect(writes).toEqual([]);
    expect(clockCalls()).toBe(0);
  });

  it("refuses a beat the outline does not hold and writes nothing", () => {
    const { service, writes } = harness({
      documents: [documentFixture(), outlineDocument(OUTLINE_CONTENT)],
    });
    // Only ## and ### headings are beats; the H1 title and preamble are not.
    for (const beat of ["Never Written", "Outline"]) {
      expect(() => service.linkChapterBeat(PRINCIPAL, "project-1", "chapter-1", { beat })).toThrow(
        new InvalidOperationError(`The outline has no beat titled "${beat}".`),
      );
    }
    expect(writes).toEqual([]);
  });

  it("refuses every link when the project has no outline document", () => {
    const { service } = harness({ documents: [documentFixture()] });
    expect(() =>
      service.linkChapterBeat(PRINCIPAL, "project-1", "chapter-1", { beat: "The Storm" }),
    ).toThrow(new InvalidOperationError('The outline has no beat titled "The Storm".'));
    expect(service.chapterBeat(PRINCIPAL, "project-1", "chapter-1")).toEqual({
      beat: null,
      candidates: [],
      outline: null,
    });
  });

  it("surfaces the store's non-chapter refusal on a link unchanged", () => {
    const refusal = new InvalidOperationError("Only chapters carry a beat association.");
    const { service } = harness({
      documents: [documentFixture(), outlineDocument(OUTLINE_CONTENT)],
      writeFailure: refusal,
    });
    let caught: unknown;
    try {
      service.linkChapterBeat(PRINCIPAL, "project-1", "chapter-1", { beat: "The Storm" });
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(refusal);
  });
});

describe("BeatAssociationService outline authority (DR-043)", () => {
  it("reads the first outline in reading order and discloses how many exist", () => {
    const first = outlineDocument(OUTLINE_CONTENT, "outline-1");
    const second = outlineDocument("## An alternate arc\n", "outline-2");
    const { service } = harness({ documents: [documentFixture(), first, second] });

    const view = service.chapterBeat(PRINCIPAL, "project-1", "chapter-1");

    expect(view.outline).toEqual({
      document_id: "outline-1",
      title: "Outline",
      outline_count: 2,
    });
    expect(view.candidates).toEqual(OUTLINE_CANDIDATES);
  });

  it("keeps non-outline documents out of the authority count", () => {
    const note = documentFixture({ id: "note-1", kind: "note", title: "Scratch" });
    const { service } = harness({
      documents: [documentFixture(), note, outlineDocument(OUTLINE_CONTENT)],
    });
    expect(service.chapterBeat(PRINCIPAL, "project-1", "chapter-1").outline).toEqual({
      document_id: "outline-1",
      title: "Outline",
      outline_count: 1,
    });
  });

  it("answers no beats for an outline without a current revision", () => {
    const { service } = harness({
      documents: [documentFixture(), outlineDocument(null)],
    });

    const view = service.chapterBeat(PRINCIPAL, "project-1", "chapter-1");

    expect(view).toEqual({
      beat: null,
      candidates: [],
      outline: { document_id: "outline-1", title: "Outline", outline_count: 1 },
    });
  });
});

describe("BeatAssociationService reads (#313)", () => {
  it("degrades a renamed heading to unlinked while refreshing the catalog", () => {
    const linked = documentFixture({ beatRef: "The Storm" });
    const renamed = outlineDocument("# Outline\n\n## The Tempest\n\nRain floods the harbour.\n");
    const { service, writes } = harness({ documents: [linked, renamed] });

    expect(service.chapterBeat(PRINCIPAL, "project-1", "chapter-1")).toEqual({
      beat: null,
      candidates: [{ title: "The Tempest" }],
      outline: { document_id: "outline-1", title: "Outline", outline_count: 1 },
    });
    expect(writes).toEqual([]);
  });

  it("resolves the stored reference by exact heading title, never case-insensitively", () => {
    const { service } = harness({
      documents: [documentFixture({ beatRef: "The Storm" }), outlineDocument(OUTLINE_CONTENT)],
    });
    expect(service.chapterBeat(PRINCIPAL, "project-1", "chapter-1").beat).toEqual({
      title: "The Storm",
      content: "Rain floods the harbour.",
    });

    const misspelled = harness({
      documents: [documentFixture({ beatRef: "the storm" }), outlineDocument(OUTLINE_CONTENT)],
    });
    expect(misspelled.service.chapterBeat(PRINCIPAL, "project-1", "chapter-1").beat).toBeNull();
  });

  it("propagates a missing document as the store's own not-found", () => {
    const failure = new NotFoundError("Document not found: ghost.");
    const { service, batchReads } = harness({ documentFailure: failure });
    let caught: unknown;
    try {
      service.chapterBeat(PRINCIPAL, "project-1", "ghost");
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(failure);
    expect(batchReads).toEqual([]);
  });
});
