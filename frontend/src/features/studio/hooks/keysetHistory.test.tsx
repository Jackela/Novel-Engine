import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness, deferred } from "@/test/harness";

import { useKeysetOlderPages } from "./keysetHistory";

interface TraversalPage {
  readonly items: readonly string[];
}

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderTraversal() {
  let current: ReturnType<typeof useKeysetOlderPages<TraversalPage>> | undefined;
  const committed: TraversalPage[] = [];
  const fetchPage = vi.fn<(cursor: string, signal: AbortSignal) => Promise<TraversalPage>>();

  function Probe(): null {
    current = useKeysetOlderPages<TraversalPage>({
      cleanupKey: "probe",
      isEnabled: () => true,
      nextCursor: "cursor-1",
      fetchPage,
      commitPage: (page) => committed.push(page),
      busyErrorMessage: "Unable to load older items.",
    });
    return null;
  }

  harness.mount(<Probe />);
  return {
    result: () => {
      if (!current) throw new Error("Expected traversal result.");
      return current;
    },
    committed,
    fetchPage,
  };
}

describe("useKeysetOlderPages", () => {
  it("keeps a successor's busy flag when a superseded read settles late (#479)", async () => {
    const supersededPage = deferred<TraversalPage>();
    const successorPage = deferred<TraversalPage>();
    const mounted = renderTraversal();
    mounted.fetchPage
      .mockReturnValueOnce(supersededPage.promise)
      .mockReturnValueOnce(successorPage.promise);

    let superseded!: Promise<void>;
    let successor!: Promise<void>;
    act(() => {
      superseded = mounted.result().loadOlder();
      mounted.result().abortInFlight();
      successor = mounted.result().loadOlder();
    });
    expect(mounted.result().isLoadingOlder).toBe(true);

    await act(async () => {
      supersededPage.resolve({ items: ["superseded"] });
      await superseded;
    });
    expect(mounted.result().isLoadingOlder).toBe(true);

    await act(async () => {
      successorPage.resolve({ items: ["successor"] });
      await successor;
    });
    expect(mounted.result().isLoadingOlder).toBe(false);
    expect(mounted.committed).toEqual([{ items: ["successor"] }]);
  });
});
