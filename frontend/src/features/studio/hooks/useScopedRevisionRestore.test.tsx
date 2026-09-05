import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";

import { useScopedRevisionRestore } from "./useScopedRevisionRestore";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

describe("useScopedRevisionRestore", () => {
  it("coalesces duplicate restores for one owner before pending state renders", async () => {
    const restore = deferred<void>();
    const handler = vi.fn(() => restore.promise);
    let current: ReturnType<typeof useScopedRevisionRestore> | undefined;

    function Wrapper(): null {
      current = useScopedRevisionRestore("project-1\u0000document-a", handler);
      return null;
    }

    harness.mount(<Wrapper />);
    let first!: Promise<void>;
    let duplicate!: Promise<void>;
    act(() => {
      first = current?.restoreRevision("revision-a") ?? Promise.resolve();
      duplicate = current?.restoreRevision("revision-a") ?? Promise.resolve();
    });

    expect(handler).toHaveBeenCalledTimes(1);
    expect(duplicate).toBe(first);
    await act(async () => {
      restore.resolve(undefined);
      await first;
    });
  });

  it("hides document A pending state and cannot clear document B when A settles late", async () => {
    const restoreA = deferred<void>();
    const restoreB = deferred<void>();
    const handlers = {
      "project-1\u0000document-a": vi.fn(() => restoreA.promise),
      "project-1\u0000document-b": vi.fn(() => restoreB.promise),
    };
    let ownerKey: keyof typeof handlers = "project-1\u0000document-a";
    let current: ReturnType<typeof useScopedRevisionRestore> | undefined;

    function Wrapper(): null {
      current = useScopedRevisionRestore(ownerKey, handlers[ownerKey]);
      return null;
    }

    const { root } = harness.mount(<Wrapper />);
    let pendingA!: Promise<void>;
    act(() => {
      pendingA = current?.restoreRevision("revision-a") ?? Promise.resolve();
    });
    expect(current?.restoringRevisionId).toBe("revision-a");

    ownerKey = "project-1\u0000document-b";
    act(() => root.render(<Wrapper />));
    expect(current?.restoringRevisionId).toBeNull();

    let pendingB!: Promise<void>;
    act(() => {
      pendingB = current?.restoreRevision("revision-b") ?? Promise.resolve();
    });
    expect(current?.restoringRevisionId).toBe("revision-b");

    ownerKey = "project-1\u0000document-a";
    act(() => root.render(<Wrapper />));
    expect(current?.restoringRevisionId).toBe("revision-a");

    await act(async () => {
      restoreA.resolve(undefined);
      await pendingA;
    });
    expect(current?.restoringRevisionId).toBeNull();

    ownerKey = "project-1\u0000document-b";
    act(() => root.render(<Wrapper />));
    expect(current?.restoringRevisionId).toBe("revision-b");

    await act(async () => {
      restoreB.resolve(undefined);
      await pendingB;
    });
    expect(current?.restoringRevisionId).toBeNull();
  });
});
