import { makeKeysetCursor } from "../../../../shared/interface/http/canonical_cursor.js";
import type { ReviewPageCursor } from "../../application/ports/review_outcome_store.js";

const cursor = makeKeysetCursor({
  version: 1,
  scopeCount: 1,
  minNumber: 0,
  numberField: "createdAtMs",
  idMaxLength: 128,
  label: "review",
});

/** Decode the opaque project-bound review-history position or fail through the validation envelope. */
export function decodeReviewCursor(token: string, routeProjectId: string): ReviewPageCursor {
  return cursor.decode(token, routeProjectId);
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeReviewCursor(
  routeProjectId: string,
  position: ReviewPageCursor | null,
): string | null {
  return cursor.encode(routeProjectId, position);
}
