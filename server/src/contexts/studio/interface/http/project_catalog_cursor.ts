import {
  decodeCanonicalCursor,
  encodeCanonicalCursor,
  invalidCursor,
} from "../../../../shared/interface/http/canonical_cursor.js";
import type { ProjectPageCursor } from "../../application/ports/project_catalog_store.js";

const CURSOR_VERSION = 1;
const PROJECT_ID_MAX_LENGTH = 128;

function isCursorTuple(value: unknown): value is [1, string, number, string] {
  if (!Array.isArray(value) || value.length !== 4) return false;
  const [version, ownerId, updatedAtMs, id] = value;
  return (
    version === CURSOR_VERSION &&
    typeof ownerId === "string" &&
    Number.isSafeInteger(updatedAtMs) &&
    updatedAtMs >= 0 &&
    typeof id === "string" &&
    id.length >= 1 &&
    id.length <= PROJECT_ID_MAX_LENGTH
  );
}

/**
 * Decode the opaque owner-bound catalog position or fail through the
 * validation envelope. The route has no project path parameter, so the
 * embedded owner scope is what binds the token to this catalog.
 */
export function decodeProjectCatalogCursor(token: string, ownerId: string): ProjectPageCursor {
  const decoded = decodeCanonicalCursor(token);
  if (!isCursorTuple(decoded) || decoded[1] !== ownerId) return invalidCursor();
  return { updatedAtMs: decoded[2], id: decoded[3] };
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeProjectCatalogCursor(
  ownerId: string,
  position: ProjectPageCursor | null,
): string | null {
  if (position === null) return null;
  if (
    !Number.isSafeInteger(position.updatedAtMs) ||
    position.updatedAtMs < 0 ||
    position.id.length < 1 ||
    position.id.length > PROJECT_ID_MAX_LENGTH
  ) {
    throw new Error("Cannot encode an invalid project catalog cursor position.");
  }
  return encodeCanonicalCursor([CURSOR_VERSION, ownerId, position.updatedAtMs, position.id]);
}
