import { describe, expect, it } from "vitest";

import {
  documentPayload,
  revisionPayload,
  revisionSummaryPayload,
} from "../../src/contexts/studio/application/payloads.js";
import { RevisionSourceInvariantError } from "../../src/contexts/studio/domain/revision_source.js";

describe("stored revision source", () => {
  it.each(["", "unknown", "author "])("refuses corrupted stored source %j", (source) => {
    const createdAt = new Date("2026-09-03T00:00:00.000Z");
    const revision = {
      id: "revision-1",
      documentId: "document-1",
      parentRevisionId: null,
      revisionNumber: 1,
      contentMarkdown: "one two",
      metadataJson: "{}",
      source,
      wordCount: 2,
      createdAt,
    };
    expect(() => revisionPayload(revision)).toThrow(RevisionSourceInvariantError);
    expect(() =>
      documentPayload({
        id: "document-1",
        projectId: "project-1",
        kind: "chapter",
        title: "Chapter",
        position: 1,
        volumeId: "volume-1",
        beatRef: null,
        loreAliasesJson: "[]",
        loreStatus: "draft",
        currentRevisionId: revision.id,
        createdAt,
        updatedAt: createdAt,
        currentRevision: revision,
      }),
    ).toThrow(RevisionSourceInvariantError);
    expect(() => revisionSummaryPayload(revision)).toThrow(RevisionSourceInvariantError);
  });
});
