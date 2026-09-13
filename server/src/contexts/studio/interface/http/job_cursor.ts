import { makeKeysetCursor } from "../../../../shared/interface/http/canonical_cursor.js";
import type { JobPageCursor } from "../../application/ports/job_records.js";

const cursor = makeKeysetCursor({
  version: 1,
  scopeCount: 1,
  minNumber: 0,
  numberField: "createdAtMs",
  idMaxLength: 128,
  label: "job",
});

/** Decode the opaque project-bound jobs position or fail through the validation envelope. */
export function decodeJobCursor(token: string, routeProjectId: string): JobPageCursor {
  return cursor.decode(token, routeProjectId);
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeJobCursor(
  routeProjectId: string,
  position: JobPageCursor | null,
): string | null {
  return cursor.encode(routeProjectId, position);
}
