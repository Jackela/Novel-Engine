import type { ExportSourceDocument } from "./ports/export_store.js";

/**
 * Canonical identity for a rendered export source.
 *
 * Array order is significant. Revision ids identify immutable prose, while
 * the remaining fields bind the stored presentation projection used by the
 * renderer. Keeping this as direct equality avoids a second persisted fact
 * and makes every identity field visible to review.
 */
export function sameExportSourceProjection(
  left: readonly ExportSourceDocument[],
  right: readonly ExportSourceDocument[],
): boolean {
  return (
    left.length === right.length &&
    left.every((item, index) => {
      const other = right[index];
      return (
        other !== undefined &&
        item.documentId === other.documentId &&
        item.revisionId === other.revisionId &&
        item.kind === other.kind &&
        item.title === other.title &&
        item.contentMarkdown === other.contentMarkdown &&
        item.metadataJson === other.metadataJson &&
        item.position === other.position
      );
    })
  );
}
