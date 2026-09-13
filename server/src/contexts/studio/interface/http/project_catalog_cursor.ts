import { makeKeysetCursor } from "../../../../shared/interface/http/canonical_cursor.js";
import type { ProjectPageCursor } from "../../application/ports/project_catalog_store.js";

const cursor = makeKeysetCursor({
  version: 1,
  scopeCount: 1,
  minNumber: 0,
  numberField: "updatedAtMs",
  idMaxLength: 128,
  label: "project catalog",
});

/**
 * Decode the opaque owner-bound catalog position or fail through the
 * validation envelope. The route has no project path parameter, so the
 * embedded owner scope is what binds the token to this catalog.
 */
export function decodeProjectCatalogCursor(token: string, ownerId: string): ProjectPageCursor {
  return cursor.decode(token, ownerId);
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeProjectCatalogCursor(
  ownerId: string,
  position: ProjectPageCursor | null,
): string | null {
  return cursor.encode(ownerId, position);
}
