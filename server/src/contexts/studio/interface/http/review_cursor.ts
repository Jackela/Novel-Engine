import {
  decodeCanonicalCursor,
  encodeCanonicalCursor,
  invalidCursor,
} from "../../../../shared/interface/http/canonical_cursor.js";
import type { ReviewPageCursor } from "../../application/ports/review_outcome_store.js";

const CURSOR_VERSION = 1;
const REVIEW_ID_MAX_LENGTH = 128;

function isCursorTuple(value: unknown): value is [1, string, number, string] {
  if (!Array.isArray(value) || value.length !== 4) return false;
  const [version, projectId, createdAtMs, id] = value;
  return (
    version === CURSOR_VERSION &&
    typeof projectId === "string" &&
    Number.isSafeInteger(createdAtMs) &&
    createdAtMs >= 0 &&
    typeof id === "string" &&
    id.length >= 1 &&
    id.length <= REVIEW_ID_MAX_LENGTH
  );
}

/** Decode the opaque project-bound review-history position or fail through the validation envelope. */
export function decodeReviewCursor(token: string, routeProjectId: string): ReviewPageCursor {
  const decoded = decodeCanonicalCursor(token);
  if (!isCursorTuple(decoded) || decoded[1] !== routeProjectId) return invalidCursor();
  return { createdAtMs: decoded[2], id: decoded[3] };
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeReviewCursor(
  routeProjectId: string,
  position: ReviewPageCursor | null,
): string | null {
  if (position === null) return null;
  if (
    !Number.isSafeInteger(position.createdAtMs) ||
    position.createdAtMs < 0 ||
    position.id.length < 1 ||
    position.id.length > REVIEW_ID_MAX_LENGTH
  ) {
    throw new Error("Cannot encode an invalid review cursor position.");
  }
  return encodeCanonicalCursor([CURSOR_VERSION, routeProjectId, position.createdAtMs, position.id]);
}
