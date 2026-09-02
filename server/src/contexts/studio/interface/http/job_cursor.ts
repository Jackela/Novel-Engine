import {
  decodeCanonicalCursor,
  encodeCanonicalCursor,
  invalidCursor,
} from "../../../../shared/interface/http/canonical_cursor.js";

const CURSOR_VERSION = 1;
const JOB_ID_MAX_LENGTH = 128;

export interface JobCursorPosition {
  readonly createdAtMs: number;
  readonly id: string;
}

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
    id.length <= JOB_ID_MAX_LENGTH
  );
}

/** Decode the opaque project-bound jobs position or fail through the validation envelope. */
export function decodeJobCursor(token: string, routeProjectId: string): JobCursorPosition {
  const decoded = decodeCanonicalCursor(token);
  if (!isCursorTuple(decoded) || decoded[1] !== routeProjectId) return invalidCursor();
  return { createdAtMs: decoded[2], id: decoded[3] };
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeJobCursor(
  routeProjectId: string,
  position: JobCursorPosition | null,
): string | null {
  if (position === null) return null;
  if (
    !Number.isSafeInteger(position.createdAtMs) ||
    position.createdAtMs < 0 ||
    position.id.length < 1 ||
    position.id.length > JOB_ID_MAX_LENGTH
  ) {
    throw new Error("Cannot encode an invalid job cursor position.");
  }
  return encodeCanonicalCursor([CURSOR_VERSION, routeProjectId, position.createdAtMs, position.id]);
}
