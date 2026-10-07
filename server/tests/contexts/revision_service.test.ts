/**
 * Direct contract tests for RevisionService (history paging, one immutable
 * body, and replay-into-restore). Fakes follow the application-boundary
 * pattern of project_settings_update.test.ts: typed method objects captured
 * through the port type, so every assertion here pins service behavior —
 * scope derived from the principal, payload projection, and the declared
 * failure semantics — and never store internals.
 */
import { describe, expect, it } from "vitest";

import type { DocumentService } from "../../src/contexts/studio/application/document_service.js";
import type {
  DocumentStore,
  RevisionPageInput,
  RevisionRecord,
  RevisionSummaryPage,
  RevisionSummaryRecord,
} from "../../src/contexts/studio/application/ports/document_store.js";
import { revisionPageLimit } from "../../src/contexts/studio/application/ports/document_store.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { RevisionService } from "../../src/contexts/studio/application/revision_service.js";
import {
  NotFoundError,
  RevisionConflictError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { RevisionSourceInvariantError } from "../../src/contexts/studio/domain/revision_source.js";
import { RevisionWordCountInvariantError } from "../../src/contexts/studio/domain/revision_word_count.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};
const NOW = new Date("2026-09-03T00:00:00.000Z");

function revision(overrides: Partial<RevisionRecord> = {}): RevisionRecord {
  return {
    id: "revision-1",
    documentId: "document-1",
    parentRevisionId: "revision-0",
    revisionNumber: 2,
    contentMarkdown: "historic A",
    metadataJson: '{"marker":"A"}',
    source: "author",
    wordCount: 2,
    createdAt: NOW,
    ...overrides,
  };
}

function summary(overrides: Partial<RevisionSummaryRecord> = {}): RevisionSummaryRecord {
  return {
    id: "revision-1",
    documentId: "document-1",
    parentRevisionId: null,
    revisionNumber: 1,
    source: "author",
    wordCount: 2,
    createdAt: NOW,
    ...overrides,
  };
}

type FakeStore = Pick<DocumentStore, "findRevisionSummaries" | "findRevision">;
type StoreWriteInput = Parameters<DocumentService["storeDocument"]>[3];
type FakeDocuments = Pick<DocumentService, "storeDocument">;
type SummaryRead = [ProjectScope, string, string, RevisionPageInput];
type RevisionRead = [ProjectScope, string, string, string];
type StoreWrite = [Principal, string, string, StoreWriteInput];

function harness(
  config: {
    page?: RevisionSummaryPage;
    revision?: RevisionRecord;
    revisionFailure?: Error;
    writeResult?: Record<string, unknown> | Error;
  } = {},
) {
  const summaryReads: SummaryRead[] = [];
  const revisionReads: RevisionRead[] = [];
  const writes: StoreWrite[] = [];
  const page: RevisionSummaryPage = config.page ?? { revisions: [], nextCursor: null };
  const store: FakeStore = {
    findRevisionSummaries: (scope, projectId, documentId, input) => {
      summaryReads.push([scope, projectId, documentId, input]);
      return page;
    },
    findRevision: (scope, projectId, documentId, revisionId) => {
      revisionReads.push([scope, projectId, documentId, revisionId]);
      if (config.revisionFailure !== undefined) throw config.revisionFailure;
      if (config.revision === undefined) throw new Error("test must provide a revision fixture");
      return config.revision;
    },
  };
  const documents: FakeDocuments = {
    storeDocument: (principal, projectId, documentId, input) => {
      writes.push([principal, projectId, documentId, input]);
      const result = config.writeResult ?? {};
      if (result instanceof Error) throw result;
      return result;
    },
  };
  return {
    summaryReads,
    revisionReads,
    writes,
    service: new RevisionService(
      store as unknown as DocumentStore,
      documents as unknown as DocumentService,
    ),
  };
}

const FIRST_SUMMARY = {
  id: "revision-1",
  document_id: "document-1",
  parent_revision_id: null,
  revision_number: 1,
  source: "author",
  word_count: 2,
  created_at: NOW.toISOString(),
};

describe("RevisionService history reads", () => {
  it("forwards the page window owner-scoped and keeps the exclusive cursor verbatim", () => {
    const nextCursor = { revisionNumber: 1, id: "revision-1" };
    const { service, summaryReads } = harness({
      page: { revisions: [summary({ id: "revision-2" }), summary()], nextCursor },
    });
    const input = { limit: revisionPageLimit(2), cursor: { revisionNumber: 9, id: "revision-9" } };

    const history = service.documentRevisions(PRINCIPAL, "project-1", "document-1", input);

    expect(summaryReads).toEqual([[{ ownerId: "owner-1" }, "project-1", "document-1", input]]);
    expect(history.revisions).toEqual([{ ...FIRST_SUMMARY, id: "revision-2" }, FIRST_SUMMARY]);
    expect(history.nextCursor).toBe(nextCursor);
  });

  it("answers an empty history page with an explicit null cursor", () => {
    const { service } = harness();
    expect(
      service.documentRevisions(PRINCIPAL, "project-1", "document-1", {
        limit: revisionPageLimit(10),
      }),
    ).toEqual({ revisions: [], nextCursor: null });
  });

  it("projects one revision body owner-scoped and never writes", () => {
    const { service, revisionReads, writes } = harness({ revision: revision() });

    const payload = service.documentRevision(PRINCIPAL, "project-1", "document-1", "revision-1");

    expect(revisionReads).toEqual([
      [{ ownerId: "owner-1" }, "project-1", "document-1", "revision-1"],
    ]);
    expect(payload).toEqual({
      id: "revision-1",
      document_id: "document-1",
      parent_revision_id: "revision-0",
      revision_number: 2,
      content_markdown: "historic A",
      metadata: { marker: "A" },
      source: "author",
      word_count: 2,
      created_at: NOW.toISOString(),
    });
    expect(writes).toEqual([]);
  });

  it("refuses a corrupted stored source or word count instead of publishing a placeholder", () => {
    const corruptedSource = harness({ revision: revision({ source: "unknown" }) });
    expect(() =>
      corruptedSource.service.documentRevision(PRINCIPAL, "p", "d", "revision-1"),
    ).toThrow(RevisionSourceInvariantError);

    const corruptedCount = harness({ revision: revision({ wordCount: null }) });
    expect(() =>
      corruptedCount.service.documentRevision(PRINCIPAL, "p", "d", "revision-1"),
    ).toThrow(RevisionWordCountInvariantError);

    const corruptedSummary = harness({
      page: { revisions: [summary({ source: "author " })], nextCursor: null },
    });
    expect(() =>
      corruptedSummary.service.documentRevisions(PRINCIPAL, "p", "d", {
        limit: revisionPageLimit(5),
      }),
    ).toThrow(RevisionSourceInvariantError);
  });

  it("propagates a missing or foreign revision as the store's own not-found", () => {
    const failure = new NotFoundError("Revision not found: revision-9.");
    const { service } = harness({ revisionFailure: failure });
    let caught: unknown;
    try {
      service.documentRevision(PRINCIPAL, "project-1", "document-1", "revision-9");
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(failure);
  });
});

describe("RevisionService replay into a restore write", () => {
  it("writes the historic body as source restore with the recorded provenance", () => {
    const { service, writes } = harness({ revision: revision() });
    const written = { current_revision_id: "revision-3" };
    const replay = harness({ revision: revision(), writeResult: written });

    const result = service.replayRevision(PRINCIPAL, "p", "d", "revision-1", "revision-2");

    expect(writes).toEqual([
      [
        PRINCIPAL,
        "p",
        "d",
        {
          contentMarkdown: "historic A",
          baseRevisionId: "revision-2",
          metadata: { marker: "A", restored_from: "revision-1" },
          source: "restore",
        },
      ],
    ]);
    expect(result).toBeDefined();

    expect(replay.service.replayRevision(PRINCIPAL, "p", "d", "revision-1", null)).toEqual(written);
    expect(replay.writes[0]?.[3].baseRevisionId).toBeNull();
  });

  it("refuses a stored restored_from key: the fresh replay id always wins", () => {
    const { service, writes } = harness({
      revision: revision({ metadataJson: '{"restored_from":"revision-0","marker":"A"}' }),
    });

    service.replayRevision(PRINCIPAL, "project-1", "document-1", "revision-7", "revision-2");

    expect(writes[0]?.[3].metadata).toEqual({ restored_from: "revision-7", marker: "A" });
  });

  it("collapses unreadable metadata JSON to the restore marker alone", () => {
    for (const metadataJson of ["not json at all", "[1,2]", "null", '"text"']) {
      const { service, writes } = harness({ revision: revision({ metadataJson }) });
      service.replayRevision(PRINCIPAL, "project-1", "document-1", "revision-1", null);
      expect(writes[0]?.[3].metadata).toEqual({ restored_from: "revision-1" });
    }
  });

  it("writes nothing when the historic revision is missing", () => {
    const failure = new NotFoundError("Revision not found: revision-9.");
    const { service, writes } = harness({ revisionFailure: failure });
    let caught: unknown;
    try {
      service.replayRevision(PRINCIPAL, "project-1", "document-1", "revision-9", null);
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(failure);
    expect(writes).toEqual([]);
  });

  it("propagates a stale base conflict from the write path unchanged", () => {
    const conflict = new RevisionConflictError("revision-2");
    const { service } = harness({ revision: revision(), writeResult: conflict });
    let caught: unknown;
    try {
      service.replayRevision(PRINCIPAL, "project-1", "document-1", "revision-1", "revision-0");
    } catch (error) {
      caught = error;
    }
    expect(caught).toBe(conflict);
    expect(conflict.currentRevisionId).toBe("revision-2");
  });
});

describe("RevisionService principal scoping", () => {
  it("refuses a principal without an owner before any dependency is consulted", () => {
    const anonymous: Principal = {
      sessionId: "session-2",
      kind: "owner",
      ownerId: null,
      expiresAt: null,
    };
    const { service, summaryReads, revisionReads, writes } = harness();
    const scoping = new Error("A principal without an owner cannot scope studio data.");
    const calls = [
      () => service.documentRevisions(anonymous, "p", "d", { limit: revisionPageLimit(5) }),
      () => service.documentRevision(anonymous, "p", "d", "revision-1"),
      () => service.replayRevision(anonymous, "p", "d", "revision-1", null),
    ];
    for (const call of calls) {
      expect(call).toThrow(scoping);
    }
    expect(summaryReads).toEqual([]);
    expect(revisionReads).toEqual([]);
    expect(writes).toEqual([]);
  });
});
