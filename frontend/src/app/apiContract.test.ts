import { describe, expect, it } from "vitest";

import { parseRevisions, parseStudioDocument } from "./apiContract";

const documentPayload = {
  id: "document-1",
  project_id: "project-1",
  kind: "chapter",
  title: "Chapter 1",
  position: 0,
  volume_id: "volume-1",
  beat_ref: null,
  lore_status: null,
  current_revision_id: "revision-1",
  content_markdown: "",
  metadata: {},
  revision_source: "author",
  word_count: 0,
  created_at: "2026-08-31T00:00:00Z",
  updated_at: "2026-08-31T00:00:00Z",
};

describe("Studio document contract", () => {
  it("requires the nullable Lore lifecycle field on every document", () => {
    const { lore_status: _omitted, ...missingLoreStatus } = documentPayload;

    expect(() => parseStudioDocument(missingLoreStatus)).toThrow("Invalid document.lore_status");
  });

  it("accepts null for non-Lore documents and a closed status for Lore documents", () => {
    expect(parseStudioDocument(documentPayload).lore_status).toBeNull();
    expect(
      parseStudioDocument({
        ...documentPayload,
        kind: "character",
        lore_status: "stable",
      }).lore_status,
    ).toBe("stable");
  });
});

describe("Revision summary page contract", () => {
  const summary = {
    id: "revision-2",
    document_id: "document-1",
    parent_revision_id: "revision-1",
    revision_number: 2,
    source: "author",
    word_count: 17,
    created_at: "2026-08-31T00:00:00Z",
  };

  it("accepts bounded History summaries without revision bodies or metadata", () => {
    expect(parseRevisions({ revisions: [summary], next_cursor: "older" })).toEqual({
      revisions: [summary],
      next_cursor: "older",
    });
  });

  it("requires the explicit nullable continuation cursor", () => {
    expect(() => parseRevisions({ revisions: [summary] })).toThrow(
      "Invalid revisions response.next_cursor",
    );
  });
});
