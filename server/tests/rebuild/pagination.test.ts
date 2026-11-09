import { describe, expect, it } from "vitest";

import { AppError } from "../../src/platform/http/error_envelope.js";
import {
  buildPageInfo,
  createCursorCodec,
  DEFAULT_PAGE_LIMIT,
  MAX_PAGE_LIMIT,
  normalizeLimit,
} from "../../src/platform/http/pagination.js";

const revisions = createCursorCodec({
  label: "revision history",
  minKey: 1,
  sortKeyMutability: "immutable",
});

const scope = ["proj-1", "doc-1"];

function expectValidationError(fn: () => unknown): void {
  try {
    fn();
  } catch (error) {
    expect(error).toBeInstanceOf(AppError);
    const appError = error as AppError;
    expect(appError.code).toBe("VALIDATION_ERROR");
    expect(appError.statusCode).toBe(422);
    // One shape for every validation failure: the AJV path already renders
    // `details.errors[]`, so an agent told to read it must not meet a second
    // layout here.
    expect(appError.message).toBe("Request validation failed.");
    const details = appError.details as {
      errors?: Array<{ field?: unknown; message?: unknown; type?: unknown }>;
    };
    expect(Array.isArray(details.errors)).toBe(true);
    expect(details.errors?.[0]?.field).toEqual(expect.any(String));
    expect(details.errors?.[0]?.message).toEqual(expect.any(String));
    expect(details.errors?.[0]?.type).toEqual(expect.any(String));
    return;
  }
  throw new Error("expected a validation failure");
}

describe("cursor codec", () => {
  it("round-trips a position with its scope", () => {
    const token = revisions.encode(scope, { key: 42, id: "rev-42" });
    expect(token).not.toBeNull();
    expect(revisions.decode(token ?? undefined, scope)).toEqual({ key: 42, id: "rev-42" });
  });

  it("returns null for an absent cursor and for a null position", () => {
    expect(revisions.encode(scope, null)).toBeNull();
    expect(revisions.decode(undefined, scope)).toBeNull();
    expect(revisions.decode("", scope)).toBeNull();
  });

  it("keeps the token inside the base64url alphabet", () => {
    const token = revisions.encode(scope, { key: 7, id: "第一章/id+with?chars" });
    expect(token).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(revisions.decode(token ?? undefined, scope)).toEqual({ key: 7, id: "第一章/id+with?chars" });
  });

  it("rejects a cursor minted for another scope", () => {
    const token = revisions.encode(["proj-1", "doc-2"], { key: 3, id: "rev-3" });
    expectValidationError(() => revisions.decode(token ?? undefined, scope));
  });

  it("rejects a cursor from another version", () => {
    const v2 = createCursorCodec({ label: "revision history", version: 2, minKey: 1 });
    const token = v2.encode(scope, { key: 3, id: "rev-3" });
    expectValidationError(() => revisions.decode(token ?? undefined, scope));
  });

  it("rejects a key below the codec minimum", () => {
    // A zero-based codec can mint key 0; the revision codec must refuse it.
    const zeroBased = createCursorCodec({ label: "revision history", minKey: 0 });
    const token = zeroBased.encode(scope, { key: 0, id: "rev-0" });
    expectValidationError(() => revisions.decode(token ?? undefined, scope));
  });

  it("rejects malformed, non-canonical, and oversized tokens", () => {
    expectValidationError(() => revisions.decode("not-a-cursor", scope));
    // Same bytes, padded spelling: a second valid cursor for one position.
    const canonical = revisions.encode(scope, { key: 5, id: "rev-5" }) ?? "";
    expectValidationError(() => revisions.decode(`${canonical}==`, scope));
    expectValidationError(() => revisions.decode("A".repeat(1025), scope));
  });

  it("refuses to encode an invalid position", () => {
    expect(() => revisions.encode(scope, { key: 0, id: "rev-0" })).toThrow(/invalid .* cursor position/);
    expect(() => revisions.encode(scope, { key: 1.5, id: "rev" })).toThrow(/invalid .* cursor position/);
  });

  it("declares whether its sort key can move", () => {
    expect(revisions.sortKeyMutability).toBe("immutable");
    const projects = createCursorCodec({ label: "project catalog", sortKeyMutability: "mutable" });
    expect(projects.sortKeyMutability).toBe("mutable");
  });
});

describe("page limits", () => {
  it("uses the default when no limit is given", () => {
    expect(normalizeLimit(undefined)).toBe(DEFAULT_PAGE_LIMIT);
  });

  it("rejects an out-of-range limit instead of silently clamping", () => {
    expectValidationError(() => normalizeLimit(0));
    expectValidationError(() => normalizeLimit(MAX_PAGE_LIMIT + 1));
    expectValidationError(() => normalizeLimit(25.9));
  });

  it("accepts the boundary values", () => {
    expect(normalizeLimit(1)).toBe(1);
    expect(normalizeLimit(MAX_PAGE_LIMIT)).toBe(MAX_PAGE_LIMIT);
  });
});

describe("page info", () => {
  it("reports a next cursor only when a surplus row exists", () => {
    expect(buildPageInfo(true, "next")).toEqual({ hasMore: true, nextCursor: "next" });
    expect(buildPageInfo(false, "next")).toEqual({ hasMore: false, nextCursor: null });
    expect(buildPageInfo(true, null)).toEqual({ hasMore: false, nextCursor: null });
  });
});
