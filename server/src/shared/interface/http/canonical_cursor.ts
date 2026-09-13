import { TextDecoder } from "node:util";

import { AppError, ERROR_CODES, ERROR_HTTP_STATUS } from "./error_envelope.js";

const CURSOR_PATTERN = /^[A-Za-z0-9_-]+$/;
const CURSOR_MAX_LENGTH = 1024;
const utf8Decoder = new TextDecoder("utf-8", { fatal: true });

/** The one public failure shape for every invalid opaque HTTP cursor. */
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

/** Encode trusted JSON cursor data without padding using Node's canonical base64url form. */
function encodeCanonicalCursor(value: unknown): string {
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
function decodeCanonicalCursor(token: string): unknown {
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

/** Declarative configuration for one resource's keyset pagination cursor. */
interface KeysetCursorConfig {
  /** Wire tuple version marker stored at index 0. */
  readonly version: number;
  /** Number of leading string scope values bound to the route: 1 or 2. */
  readonly scopeCount: 1 | 2;
  /** Inclusive minimum of the numeric ordering field (0 for timestamps, 1 for one-based ordinals). */
  readonly minNumber: number;
  /** Property name of the numeric ordering field in the decoded position. */
  readonly numberField: string;
  /** Maximum allowed length of the trailing identity value. */
  readonly idMaxLength: number;
  /** Resource label interpolated verbatim into the encode-failure error message. */
  readonly label: string;
}

/** Persistence-neutral exclusive keyset position: the numeric ordering field plus a tiebreaker id. */
type KeysetPagePosition<Field extends string> = {
  readonly id: string;
} & Readonly<Record<Field, number>>;

type KeysetDecoder<Scopes extends 1 | 2, Position> = Scopes extends 2
  ? (token: string, scopeA: string, scopeB: string) => Position
  : (token: string, scope: string) => Position;

type KeysetEncoder<Scopes extends 1 | 2, Position> = Scopes extends 2
  ? (scopeA: string, scopeB: string, position: Position | null) => string | null
  : (scope: string, position: Position | null) => string | null;

/**
 * Build one resource's cursor codec from its declarative wire contract.
 * The wire format is `[version, ...scopes, numberField, id]`; decode fails
 * through the shared validation envelope, encode throws on untrusted input.
 */
export function makeKeysetCursor<const Config extends KeysetCursorConfig>(config: Config) {
  type Field = Config["numberField"] & string;
  type Scopes = Config["scopeCount"];
  type Position = KeysetPagePosition<Field>;

  const tupleLength = config.scopeCount + 3;
  const numberIndex = config.scopeCount + 1;
  const idIndex = config.scopeCount + 2;
  const numberField: Field = config.numberField;

  function isCursorTuple(value: unknown): value is readonly unknown[] {
    if (!Array.isArray(value) || value.length !== tupleLength) return false;
    if (value[0] !== config.version) return false;
    for (let index = 1; index <= config.scopeCount; index += 1) {
      if (typeof value[index] !== "string") return false;
    }
    const orderValue = value[numberIndex];
    if (
      typeof orderValue !== "number" ||
      !Number.isSafeInteger(orderValue) ||
      orderValue < config.minNumber
    ) {
      return false;
    }
    const id = value[idIndex];
    return typeof id === "string" && id.length >= 1 && id.length <= config.idMaxLength;
  }

  function decodeWith(token: string, scopes: readonly string[]): Position {
    const decoded = decodeCanonicalCursor(token);
    if (!isCursorTuple(decoded)) return invalidCursor();
    for (let index = 0; index < scopes.length; index += 1) {
      if (decoded[index + 1] !== scopes[index]) return invalidCursor();
    }
    return {
      [config.numberField]: decoded[numberIndex],
      id: decoded[idIndex],
    } as Position;
  }

  function encodeWith(scopes: readonly string[], position: Position | null): string | null {
    if (position === null) return null;
    const orderValue = position[numberField];
    if (
      !Number.isSafeInteger(orderValue) ||
      orderValue < config.minNumber ||
      position.id.length < 1 ||
      position.id.length > config.idMaxLength
    ) {
      throw new Error(`Cannot encode an invalid ${config.label} cursor position.`);
    }
    return encodeCanonicalCursor([config.version, ...scopes, orderValue, position.id]);
  }

  return {
    decode: ((token: string, ...scopes: string[]) => decodeWith(token, scopes)) as KeysetDecoder<
      Scopes,
      Position
    >,
    encode: ((...args: unknown[]) => {
      const scopes = args.slice(0, -1) as string[];
      const position = args[args.length - 1] as Position | null;
      return encodeWith(scopes, position);
    }) as KeysetEncoder<Scopes, Position>,
  };
}
