import { TextDecoder } from "node:util";
import {
  AppError,
  ERROR_CODES,
  ERROR_HTTP_STATUS,
} from "../../../../shared/interface/http/error_envelope.js";
import type { RevisionPageCursor } from "../../application/ports/studio_store.js";

const CURSOR_VERSION = 1;
const CURSOR_PATTERN = /^[A-Za-z0-9_-]+$/;
const CURSOR_MAX_LENGTH = 1024;
const REVISION_ID_MAX_LENGTH = 128;
const utf8Decoder = new TextDecoder("utf-8", { fatal: true });

function invalidCursor(): never {
  throw new AppError({
    statusCode: ERROR_HTTP_STATUS[ERROR_CODES.VALIDATION_ERROR],
    code: ERROR_CODES.VALIDATION_ERROR,
    message: "Request validation failed.",
    details: {
      errors: [{ field: "cursor", message: "value is invalid", type: "invalid" }],
    },
  });
}

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
  if (token.length < 1 || token.length > CURSOR_MAX_LENGTH || !CURSOR_PATTERN.test(token)) {
    return invalidCursor();
  }
  let decoded: unknown;
  try {
    const bytes = Buffer.from(token, "base64url");
    if (bytes.toString("base64url") !== token) return invalidCursor();
    decoded = JSON.parse(utf8Decoder.decode(bytes));
  } catch {
    return invalidCursor();
  }
  if (!isCursorTuple(decoded) || decoded[1] !== routeProjectId || decoded[2] !== routeDocumentId) {
    return invalidCursor();
  }
  const position = { revisionNumber: decoded[3], id: decoded[4] };
  if (encodeRevisionCursor(routeProjectId, routeDocumentId, position) !== token) {
    return invalidCursor();
  }
  return position;
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
  return Buffer.from(
    JSON.stringify([
      CURSOR_VERSION,
      routeProjectId,
      routeDocumentId,
      position.revisionNumber,
      position.id,
    ]),
    "utf8",
  ).toString("base64url");
}
