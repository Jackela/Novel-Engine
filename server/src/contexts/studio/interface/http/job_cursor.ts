import { TextDecoder } from "node:util";

import {
  AppError,
  ERROR_CODES,
  ERROR_HTTP_STATUS,
} from "../../../../shared/interface/http/error_envelope.js";

const CURSOR_VERSION = 1;
const CURSOR_PATTERN = /^[A-Za-z0-9_-]+$/;
const CURSOR_MAX_LENGTH = 1024;
const JOB_ID_MAX_LENGTH = 128;
const utf8Decoder = new TextDecoder("utf-8", { fatal: true });

export interface JobCursorPosition {
  readonly createdAtMs: number;
  readonly id: string;
}

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
  if (!isCursorTuple(decoded) || decoded[1] !== routeProjectId) return invalidCursor();
  const position = { createdAtMs: decoded[2], id: decoded[3] };
  if (encodeJobCursor(routeProjectId, position) !== token) return invalidCursor();
  return position;
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
  return Buffer.from(
    JSON.stringify([CURSOR_VERSION, routeProjectId, position.createdAtMs, position.id]),
    "utf8",
  ).toString("base64url");
}
