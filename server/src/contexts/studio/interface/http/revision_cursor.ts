import {
  decodeCanonicalCursor,
  encodeCanonicalCursor,
  invalidCursor,
} from "../../../../shared/interface/http/canonical_cursor.js";
import type { RevisionPageCursor } from "../../application/ports/studio_store.js";

const CURSOR_VERSION = 1;
const REVISION_ID_MAX_LENGTH = 128;

function isCursorTuple(value: unknown): value is [1, string, string, number, string] {
  if (!Array.isArray(value) || value.length !== 5) return false;
  const [version, projectId, documentId, revisionNumber, id] = value;
  return (
    version === CURSOR_VERSION &&
    typeof projectId === "string" &&
    typeof documentId === "string" &&
    Number.isSafeInteger(revisionNumber) &&
    revisionNumber > 0 &&
    typeof id === "string" &&
    id.length >= 1 &&
    id.length <= REVISION_ID_MAX_LENGTH
  );
}

/** Decode one canonical opaque route-bound revision-history position. */
export function decodeRevisionCursor(
  token: string,
  routeProjectId: string,
  routeDocumentId: string,
): RevisionPageCursor {
  const decoded = decodeCanonicalCursor(token);
  if (!isCursorTuple(decoded) || decoded[1] !== routeProjectId || decoded[2] !== routeDocumentId) {
    return invalidCursor();
  }
  return { revisionNumber: decoded[3], id: decoded[4] };
}

/** Encode a trusted application position into the versioned wire token. */
export function encodeRevisionCursor(
  routeProjectId: string,
  routeDocumentId: string,
  position: RevisionPageCursor | null,
): string | null {
  if (position === null) return null;
  if (
    !Number.isSafeInteger(position.revisionNumber) ||
    position.revisionNumber <= 0 ||
    position.id.length < 1 ||
    position.id.length > REVISION_ID_MAX_LENGTH
  ) {
    throw new Error("Cannot encode an invalid revision cursor position.");
  }
  return encodeCanonicalCursor([
    CURSOR_VERSION,
    routeProjectId,
    routeDocumentId,
    position.revisionNumber,
    position.id,
  ]);
}
