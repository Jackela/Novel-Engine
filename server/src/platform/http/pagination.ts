/**
 * One keyset-pagination codec for every list endpoint.
 *
 * The previous code carried five near-identical cursor modules. They agreed on
 * the wire shape (a positional tuple) but each bound its own scope and version,
 * and two of them disagreed on how a nullable sort key was encoded. This module
 * keeps the wire contract exactly as the old `canonical_cursor` had it, and adds
 * only what the five shared: one entry point.
 *
 * Wire shape: `base64url([version, ...scope, key, id])`
 * - `version` lets one list evolve its cursor without invalidating the others.
 * - `scope` binds the cursor to its resource (project id, document id, owner
 *   id). A cursor minted for one document cannot be replayed against another:
 *   decoding fails instead of quietly returning a page from the wrong place.
 * - `key` is a non-negative safe integer (epoch milliseconds, or a 1-based
 *   ordinal). It is never a string: the SQL columns it compares against are
 *   integers, and SQLite compares integers and text by storage class.
 * - `id` is the unique tie-breaker.
 *
 * Hardening carried over from `canonical_cursor.ts`, deliberately unchanged:
 * 1–1024 characters, `^[A-Za-z0-9_-]+$`, strict UTF-8, and a re-encode equality
 * check. Without the re-encode check, alternate base64 spellings of the same
 * bytes become a second valid cursor for one position.
 */

import { AppError } from "./error_envelope.js";

export const DEFAULT_PAGE_LIMIT = 50;
export const MAX_PAGE_LIMIT = 100;

const MIN_CURSOR_LENGTH = 1;
const MAX_CURSOR_LENGTH = 1024;
const CURSOR_PATTERN = /^[A-Za-z0-9_-]+$/;
const DEFAULT_MAX_ID_LENGTH = 128;

export interface CursorPosition {
  readonly key: number;
  readonly id: string;
}

/**
 * Whether the sort key can change after a row is written.
 *
 * `immutable` (revision number, creation time) means a page walk is stable.
 * `mutable` (project `updatedAt`) means a concurrent write can move a row
 * across the page boundary, so the walk may skip or repeat it. Callers must
 * either accept that or sort by an immutable column.
 */
export type SortKeyMutability = "immutable" | "mutable";

export interface CursorCodecOptions {
  /** Resource name; appears in encode diagnostics only. */
  readonly label: string;
  readonly version?: number;
  /** Smallest legal key: 0 for epoch milliseconds, 1 for ordinals. */
  readonly minKey?: number;
  readonly sortKeyMutability?: SortKeyMutability;
  readonly maxIdLength?: number;
}

export interface CursorCodec {
  readonly label: string;
  readonly version: number;
  readonly sortKeyMutability: SortKeyMutability;
  /** Encodes a position, or returns null when the walk has ended. */
  encode(scope: readonly string[], position: CursorPosition | null): string | null;
  /** Decodes a token for this scope; throws a 422 AppError when it does not fit. */
  decode(token: string | undefined, scope: readonly string[]): CursorPosition | null;
}

/**
 * Every validation failure renders the same shape: a fixed sentence plus
 * `details.errors[]` carrying the field. The AJV path already does this, and an
 * agent told to "read details.errors" must not hit a second layout here.
 */
function invalid(field: string, message: string): AppError {
  return new AppError("VALIDATION_ERROR", {
    message: "Request validation failed.",
    details: { errors: [{ field, message, type: "invalid" }] },
  });
}

/** Clamp-free limit normalization: an out-of-range limit is a client bug. */
export function normalizeLimit(raw: number | undefined): number {
  if (raw === undefined) return DEFAULT_PAGE_LIMIT;
  if (!Number.isInteger(raw) || raw < 1 || raw > MAX_PAGE_LIMIT) {
    throw invalid(
      "limit",
      `limit must be an integer between 1 and ${String(MAX_PAGE_LIMIT)}; received ${String(raw)}.`,
    );
  }
  return raw;
}

export function createCursorCodec(options: CursorCodecOptions): CursorCodec {
  const label = options.label;
  const version = options.version ?? 1;
  const minKey = options.minKey ?? 0;
  const sortKeyMutability = options.sortKeyMutability ?? "immutable";
  const maxIdLength = options.maxIdLength ?? DEFAULT_MAX_ID_LENGTH;

  function encode(scope: readonly string[], position: CursorPosition | null): string | null {
    if (position === null) return null;
    if (!Number.isSafeInteger(position.key) || position.key < minKey) {
      throw new Error(`Cannot encode an invalid ${label} cursor position.`);
    }
    const payload = [version, ...scope, position.key, position.id];
    return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
  }

  function decode(token: string | undefined, scope: readonly string[]): CursorPosition | null {
    if (token === undefined || token === "") return null;
    if (token.length < MIN_CURSOR_LENGTH || token.length > MAX_CURSOR_LENGTH) {
      throw invalid("cursor", `The ${label} cursor length is out of range.`);
    }
    if (!CURSOR_PATTERN.test(token)) {
      throw invalid(
        "cursor",
        `The ${label} cursor contains characters outside the base64url alphabet.`,
      );
    }
    let decoded: string;
    try {
      decoded = Buffer.from(token, "base64url").toString("utf8");
    } catch {
      throw invalid("cursor", `The ${label} cursor is not valid base64url.`);
    }
    // Canonical-form check: re-encoding must reproduce the exact token.
    if (Buffer.from(decoded, "utf8").toString("base64url") !== token) {
      throw invalid("cursor", `The ${label} cursor is not in canonical form.`);
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(decoded);
    } catch {
      throw invalid("cursor", `The ${label} cursor does not contain JSON.`);
    }
    if (!Array.isArray(parsed)) {
      throw invalid("cursor", `The ${label} cursor is not a positional tuple.`);
    }
    const expectedLength = 1 + scope.length + 2;
    if (parsed.length !== expectedLength) {
      throw invalid(
        "cursor",
        `The ${label} cursor has ${String(parsed.length)} fields; expected ${String(expectedLength)}.`,
      );
    }
    if (parsed[0] !== version) {
      throw invalid(
        "cursor",
        `The ${label} cursor version is not supported; expected ${String(version)}.`,
      );
    }
    for (let index = 0; index < scope.length; index += 1) {
      if (parsed[1 + index] !== scope[index]) {
        throw invalid("cursor", `The ${label} cursor belongs to a different scope.`);
      }
    }
    const key = parsed[1 + scope.length];
    const id = parsed[2 + scope.length];
    if (typeof key !== "number" || !Number.isSafeInteger(key) || key < minKey) {
      throw invalid("cursor", `The ${label} cursor key is out of range.`);
    }
    if (typeof id !== "string" || id.length === 0 || id.length > maxIdLength) {
      throw invalid("cursor", `The ${label} cursor id is out of range.`);
    }
    return { key, id };
  }

  return { label, version, sortKeyMutability, encode, decode };
}

export interface PageInfo {
  readonly nextCursor: string | null;
  readonly hasMore: boolean;
}

/**
 * Build page info from the fetch-limit-plus-one pattern: callers read
 * `limit + 1` rows, pass the surplus flag here, and cursor the last kept row.
 */
export function buildPageInfo(hasSurplus: boolean, nextCursor: string | null): PageInfo {
  return hasSurplus && nextCursor !== null
    ? { hasMore: true, nextCursor }
    : { hasMore: false, nextCursor: null };
}
