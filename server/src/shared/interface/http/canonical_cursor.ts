import { TextDecoder } from "node:util";

import { AppError, ERROR_CODES, ERROR_HTTP_STATUS } from "./error_envelope.js";

const CURSOR_PATTERN = /^[A-Za-z0-9_-]+$/;
const CURSOR_MAX_LENGTH = 1024;
const utf8Decoder = new TextDecoder("utf-8", { fatal: true });

/** The one public failure shape for every invalid opaque HTTP cursor. */
export function invalidCursor(): never {
  throw new AppError({
    statusCode: ERROR_HTTP_STATUS[ERROR_CODES.VALIDATION_ERROR],
    code: ERROR_CODES.VALIDATION_ERROR,
    message: "Request validation failed.",
    details: {
      errors: [{ field: "cursor", message: "value is invalid", type: "invalid" }],
    },
  });
}

/** Encode trusted JSON cursor data without padding using Node's canonical base64url form. */
export function encodeCanonicalCursor(value: unknown): string {
  const json = JSON.stringify(value);
  if (json === undefined) {
    throw new TypeError("Canonical cursor data must be JSON serializable.");
  }
  return Buffer.from(json, "utf8").toString("base64url");
}

/**
 * Decode only canonical base64url, fatal UTF-8, and canonical JSON bytes.
 * Tuple shape, version, identity, and range remain owned by each route.
 */
export function decodeCanonicalCursor(token: string): unknown {
  if (token.length < 1 || token.length > CURSOR_MAX_LENGTH || !CURSOR_PATTERN.test(token)) {
    return invalidCursor();
  }
  let decoded: unknown;
  let canonicalBase64Url: string;
  try {
    const bytes = Buffer.from(token, "base64url");
    canonicalBase64Url = bytes.toString("base64url");
    decoded = JSON.parse(utf8Decoder.decode(bytes));
  } catch {
    return invalidCursor();
  }
  if (canonicalBase64Url !== token || encodeCanonicalCursor(decoded) !== token) {
    return invalidCursor();
  }
  return decoded;
}
