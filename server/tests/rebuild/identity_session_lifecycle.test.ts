import { describe, expect, it } from "vitest";

import type { SessionRecord, SessionStore } from "../../src/slices/identity/ports.js";
import { logout } from "../../src/slices/identity/usecases/logout.js";
import { resolvePrincipal } from "../../src/slices/identity/usecases/resolve_principal.js";

const NOW = 1_700_000_000_000;
const GOOD_TOKEN = "good-token";
const GOOD_DIGEST = "digest:good-token";

function session(overrides: Partial<SessionRecord> = {}): SessionRecord {
  return {
    id: "session-1",
    ownerId: "owner-1",
    tokenHash: GOOD_DIGEST,
    csrfToken: "csrf-1",
    expiresAt: NOW + 1_000,
    lastSeenAt: NOW - 500,
    createdAt: NOW - 500,
    ...overrides,
  };
}

interface Harness {
  readonly deps: Parameters<typeof resolvePrincipal>[0];
  readonly deleted: string[];
  readonly touched: Array<{ id: string; now: number }>;
  readonly lookups: () => number;
}

function harness(options: { record?: SessionRecord | null } = {}): Harness {
  const deleted: string[] = [];
  const touched: Array<{ id: string; now: number }> = [];
  let lookups = 0;
  const record = options.record ?? null;

  const sessions: SessionStore = {
    create: () => {
      throw new Error("lifecycle paths never create sessions");
    },
    findByTokenHash: (hash) => {
      lookups += 1;
      return record !== null && record.tokenHash === hash ? record : null;
    },
    delete: (id) => {
      deleted.push(id);
    },
    touch: (id, now) => {
      touched.push({ id, now });
    },
  };

  return {
    deleted,
    touched,
    lookups: () => lookups,
    deps: {
      sessions,
      tokens: {
        issue: () => {
          throw new Error("issue is not part of resolution");
        },
        derive: (token) => (token === GOOD_TOKEN ? GOOD_DIGEST : `digest:${token}`),
      },
      now: () => NOW,
    },
  };
}

describe("logout", () => {
  it("deletes the matching session", () => {
    const h = harness({ record: session() });
    logout({ sessions: h.deps.sessions, tokens: h.deps.tokens }, GOOD_TOKEN);
    expect(h.deleted).toEqual(["session-1"]);
  });

  it("is a no-op for an unknown token", () => {
    const h = harness({ record: session() });
    logout({ sessions: h.deps.sessions, tokens: h.deps.tokens }, "some-other-token");
    expect(h.deleted).toEqual([]);
  });

  it("does not even look up when no token is presented", () => {
    const h = harness({ record: session() });
    logout({ sessions: h.deps.sessions, tokens: h.deps.tokens }, undefined);
    expect(h.lookups()).toBe(0);
    expect(h.deleted).toEqual([]);
  });
});

describe("resolvePrincipal", () => {
  it("returns the principal and refreshes last-seen for a live session", () => {
    const h = harness({ record: session() });
    expect(resolvePrincipal(h.deps, GOOD_TOKEN)).toEqual({
      sessionId: "session-1",
      ownerId: "owner-1",
      expiresAt: NOW + 1_000,
    });
    expect(h.touched).toEqual([{ id: "session-1", now: NOW }]);
    expect(h.deleted).toEqual([]);
  });

  it("deletes an expired session and reports it as absent", () => {
    const h = harness({ record: session({ expiresAt: NOW }) });
    expect(resolvePrincipal(h.deps, GOOD_TOKEN)).toBeNull();
    expect(h.deleted).toEqual(["session-1"]);
    // An expired session must not be touched: that would look like activity.
    expect(h.touched).toEqual([]);
  });

  it("returns null for an unknown token without touching anything", () => {
    const h = harness({ record: session() });
    expect(resolvePrincipal(h.deps, "unknown")).toBeNull();
    expect(h.touched).toEqual([]);
    expect(h.deleted).toEqual([]);
  });

  it("does not query the store for an empty token", () => {
    const h = harness({ record: session() });
    expect(resolvePrincipal(h.deps, "")).toBeNull();
    expect(h.lookups()).toBe(0);
  });
});
