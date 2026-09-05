import { describe, expect, it } from "vitest";

import {
  parseDocumentSummaries,
  parseProjectListItem,
  parseProjectShell,
  parseStudioDocument,
} from "./apiContract";

const projectScalars = {
  id: "project-1",
  title: "Harbor",
  description: "",
  settings: {},
  import_hash: null,
  created_at: "2026-09-03T00:00:00Z",
  updated_at: "2026-09-03T00:00:00Z",
};

const summary = {
  id: "document-1",
  project_id: "project-1",
  kind: "chapter",
  title: "Chapter 1",
  position: 0,
  volume_id: null,
  beat_ref: null,
  lore_status: null,
  current_revision_id: "revision-1",
  revision_source: "author",
  word_count: 12,
  created_at: "2026-09-03T00:00:00Z",
  updated_at: "2026-09-03T00:00:00Z",
};

const completeDocument = {
  ...summary,
  content_markdown: "Twelve accepted words.",
  metadata: {},
};

describe("bounded project contracts", () => {
  it("parses a closed project catalog item independently from a project shell", () => {
    expect(parseProjectListItem(projectScalars)).toEqual(projectScalars);
    expect(() => parseProjectListItem({ ...projectScalars, documents: [] })).toThrow(
      "Invalid project list item keys",
    );
  });

  it("parses exact document summaries and rejects legacy body-bearing rows", () => {
    expect(parseDocumentSummaries({ documents: [summary] })).toEqual({ documents: [summary] });
    expect(() => parseDocumentSummaries({ documents: [completeDocument] })).toThrow(
      "Invalid documents[0] keys",
    );
  });

  it("requires nonnegative integer summary counts", () => {
    for (const wordCount of [-1, 1.5, Number.POSITIVE_INFINITY]) {
      expect(() =>
        parseDocumentSummaries({ documents: [{ ...summary, word_count: wordCount }] }),
      ).toThrow("Invalid documents[0].word_count");
    }
  });

  it("keeps the project shell and complete current Document shapes distinct", () => {
    expect(parseProjectShell({ ...projectScalars, documents: [summary], volumes: [] })).toEqual({
      ...projectScalars,
      documents: [summary],
      volumes: [],
    });
    expect(() =>
      parseProjectShell({ ...projectScalars, documents: [completeDocument], volumes: [] }),
    ).toThrow("Invalid project shell.documents[0] keys");
    expect(() => parseStudioDocument(summary)).toThrow("Invalid document.content_markdown");
    expect(parseStudioDocument(completeDocument)).toEqual(completeDocument);
  });
});
