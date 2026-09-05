import { describe, expect, it } from "vitest";
import { sameExportSourceProjection } from "../../src/contexts/studio/application/export_source_identity.js";
import type { ExportSourceDocument } from "../../src/contexts/studio/application/ports/export_store.js";

const first: ExportSourceDocument = {
  documentId: "document-1",
  revisionId: "revision-1",
  kind: "chapter",
  title: "Chapter 1",
  contentMarkdown: "First prose.",
  metadataJson: '{"pov":"Mara"}',
  position: 1,
};
const second: ExportSourceDocument = {
  documentId: "document-2",
  revisionId: "revision-2",
  kind: "chapter",
  title: "Chapter 2",
  contentMarkdown: "Second prose.",
  metadataJson: "{}",
  position: 2,
};

describe("canonical export source identity", () => {
  it("is deterministic and order-sensitive", () => {
    expect(sameExportSourceProjection([first, second], [{ ...first }, { ...second }])).toBe(true);
    expect(sameExportSourceProjection([first, second], [second, first])).toBe(false);
    expect(sameExportSourceProjection([first], [first, second])).toBe(false);
  });

  it.each([
    ["documentId", "document-other"],
    ["revisionId", "revision-other"],
    ["kind", "outline"],
    ["title", "Retitled"],
    ["contentMarkdown", "Changed prose."],
    ["metadataJson", '{"pov":"Ilya"}'],
    ["position", 2],
  ] as const)("treats a changed %s as a different source", (field, value) => {
    expect(sameExportSourceProjection([first], [{ ...first, [field]: value }])).toBe(false);
  });
});
