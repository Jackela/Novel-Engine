import { makeKeysetCursor } from "../../../../shared/interface/http/canonical_cursor.js";
import type { RevisionPageCursor } from "../../application/ports/document_store.js";

const cursor = makeKeysetCursor({
  version: 1,
  scopeCount: 2,
  minNumber: 1,
  numberField: "revisionNumber",
  idMaxLength: 128,
  label: "revision",
});

/** Decode one canonical opaque route-bound revision-history position. */
export function decodeRevisionCursor(
  token: string,
  routeProjectId: string,
  routeDocumentId: string,
): RevisionPageCursor {
  return cursor.decode(token, routeProjectId, routeDocumentId);
}

/** Encode a trusted application position into the versioned wire token. */
export function encodeRevisionCursor(
  routeProjectId: string,
  routeDocumentId: string,
  position: RevisionPageCursor | null,
): string | null {
  return cursor.encode(routeProjectId, routeDocumentId, position);
}
