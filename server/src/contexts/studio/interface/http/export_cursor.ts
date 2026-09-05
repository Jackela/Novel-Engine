import {
  decodeCanonicalCursor,
  encodeCanonicalCursor,
  invalidCursor,
} from "../../../../shared/interface/http/canonical_cursor.js";

const CURSOR_VERSION = 1;
const EXPORT_ID_MAX_LENGTH = 128;

export interface ExportCursorPosition {
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
    id.length <= EXPORT_ID_MAX_LENGTH
  );
}

/** Decode the opaque project-bound export catalog position or fail through the validation envelope. */
export function decodeExportCursor(token: string, routeProjectId: string): ExportCursorPosition {
  const decoded = decodeCanonicalCursor(token);
  if (!isCursorTuple(decoded) || decoded[1] !== routeProjectId) return invalidCursor();
  return { createdAtMs: decoded[2], id: decoded[3] };
}

/** Encode a trusted application position as the versioned opaque wire token. */
export function encodeExportCursor(
  routeProjectId: string,
  position: ExportCursorPosition | null,
): string | null {
  if (position === null) return null;
  if (
    !Number.isSafeInteger(position.createdAtMs) ||
    position.createdAtMs < 0 ||
    position.id.length < 1 ||
    position.id.length > EXPORT_ID_MAX_LENGTH
  ) {
    throw new Error("Cannot encode an invalid export cursor position.");
  }
  return encodeCanonicalCursor([CURSOR_VERSION, routeProjectId, position.createdAtMs, position.id]);
}
