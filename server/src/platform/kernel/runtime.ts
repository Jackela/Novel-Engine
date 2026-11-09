/**
 * Time and identity, injected rather than imported.
 *
 * Use cases never call `Date.now()` or `randomUUID()` directly: tests need a
 * frozen clock (revision ordering, retention windows, snapshot timestamps) and
 * a predictable id sequence (cursor stability, golden files).
 */

export interface Clock {
  /** Unix seconds. Revisions, snapshots, and exports all store seconds. */
  nowSeconds(): number;
}

export const systemClock: Clock = {
  nowSeconds: () => Math.floor(Date.now() / 1000),
};

export interface IdGenerator {
  /** A new opaque identifier; unique within the process and across restarts. */
  next(): string;
}

export const randomIds: IdGenerator = {
  next: () => crypto.randomUUID(),
};

/** A clock that never advances and an id sequence, for tests and fixtures. */
export function frozenRuntime(startSeconds = 1_700_000_000): {
  clock: Clock;
  ids: IdGenerator;
} {
  let seconds = startSeconds;
  let counter = 0;
  return {
    clock: {
      nowSeconds: () => seconds++,
    },
    ids: {
      next: () => `id-${String(++counter).padStart(6, "0")}`,
    },
  };
}
