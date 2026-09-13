import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RevisionPage } from "@/app/types/studio";
import { revision } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { resetRevisionCacheForTests, useRevisionCache } from "./useRevisionCache";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return { ...actual, api: { ...actual.api, revisions: vi.fn<typeof actual.api.revisions>() } };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  vi.resetAllMocks();
});

function renderSubscribers() {
  let showInitiator = true;
  const initiator = { onError: vi.fn(), onSuccess: vi.fn() };
  const survivor = { onError: vi.fn(), onSuccess: vi.fn() };
  function Consumer({ callbacks }: { callbacks: typeof survivor }): null {
    useRevisionCache("project-1", "document-1", callbacks.onError, callbacks.onSuccess);
    return null;
  }
  function Wrapper() {
    return (
      <>
        {showInitiator ? <Consumer callbacks={initiator} /> : null}
        <Consumer callbacks={survivor} />
      </>
    );
  }
  const { root } = harness.mount(<Wrapper />);
  return {
    initiator,
    survivor,
    removeInitiator: () => {
      showInitiator = false;
      act(() => root.render(<Wrapper />));
    },
  };
}

describe("useRevisionCache coalesced subscribers", () => {
  it("notifies the surviving subscriber when the initiator unmounts before success", async () => {
    const page = deferred<RevisionPage>();
    vi.mocked(api.revisions).mockReturnValue(page.promise);
    const view = renderSubscribers();
    expect(api.revisions).toHaveBeenCalledTimes(1);
    view.removeInitiator();

    await act(async () => {
      page.resolve({ revisions: [revision("revision-1")], next_cursor: null });
      await page.promise;
    });

    expect(view.initiator.onSuccess).not.toHaveBeenCalled();
    expect(view.survivor.onSuccess).toHaveBeenCalledTimes(1);
  });

  it("reports a coalesced failure only to subscribers still mounted", async () => {
    let rejectPage!: (reason: unknown) => void;
    const page = new Promise<RevisionPage>((_resolve, reject) => {
      rejectPage = reject;
    });
    vi.mocked(api.revisions).mockReturnValue(page);
    const view = renderSubscribers();
    view.removeInitiator();

    await act(async () => {
      rejectPage(new Error("history offline"));
      await page.catch(() => undefined);
    });

    expect(view.initiator.onError).not.toHaveBeenCalled();
    expect(view.survivor.onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "history offline" }),
    );
  });

  it("does not reinterpret an undefined rejection as success", async () => {
    let rejectPage!: (reason?: unknown) => void;
    const page = new Promise<RevisionPage>((_resolve, reject) => {
      rejectPage = reject;
    });
    vi.mocked(api.revisions).mockReturnValue(page);
    const view = renderSubscribers();

    await act(async () => {
      rejectPage(undefined);
      await page.catch(() => undefined);
    });

    expect(view.survivor.onError).toHaveBeenCalledWith(undefined);
    expect(view.survivor.onSuccess).not.toHaveBeenCalled();
  });

  it("does not let a later subscriber activation supersede a mutation refresh", async () => {
    const refresh = deferred<RevisionPage>();
    const refreshed = revision("revision-created");
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [revision("revision-initial")], next_cursor: null })
      .mockReturnValueOnce(refresh.promise);
    const firstCallbacks = { onError: vi.fn(), onSuccess: vi.fn() };
    const secondCallbacks = { onError: vi.fn(), onSuccess: vi.fn() };
    let firstResult: ReturnType<typeof useRevisionCache> | undefined;
    function Consumer({ callbacks }: { callbacks: typeof firstCallbacks }): null {
      const result = useRevisionCache(
        "project-1",
        "document-1",
        callbacks.onError,
        callbacks.onSuccess,
      );
      if (callbacks === firstCallbacks) firstResult = result;
      return null;
    }
    harness.mount(<Consumer callbacks={firstCallbacks} />);
    await flushEffects();
    firstCallbacks.onSuccess.mockClear();

    let mutationRefresh: Promise<void> | undefined;
    act(() => {
      mutationRefresh = firstResult?.refreshDocumentRevisions("document-1", refreshed.id);
    });
    const refreshInit = vi.mocked(api.revisions).mock.calls[1]?.[2];
    harness.mount(<Consumer callbacks={secondCallbacks} />);

    expect(api.revisions).toHaveBeenCalledTimes(2);
    expect(refreshInit?.signal?.aborted).toBe(false);
    await act(async () => {
      refresh.resolve({ revisions: [refreshed], next_cursor: null });
      await mutationRefresh;
    });
    expect(firstCallbacks.onSuccess).toHaveBeenCalledTimes(1);
    expect(secondCallbacks.onSuccess).toHaveBeenCalledTimes(1);
  });

  it("aborts the request and settles queued older work after the last subscriber unmounts", async () => {
    const refresh = deferred<RevisionPage>();
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [revision("revision-initial")], next_cursor: "older" })
      .mockReturnValueOnce(refresh.promise);
    let result: ReturnType<typeof useRevisionCache> | undefined;
    function Consumer(): null {
      result = useRevisionCache("project-1", "document-1", vi.fn());
      return null;
    }
    const mounted = harness.mount(<Consumer />);
    await flushEffects();
    let older!: Promise<void>;
    act(() => {
      void result?.refreshDocumentRevisions("document-1", "revision-created");
      older = result?.loadOlderRevisions() ?? Promise.resolve();
    });
    const refreshInit = vi.mocked(api.revisions).mock.calls[1]?.[2];

    harness.unmount(mounted.container);
    await act(async () => older);

    expect(refreshInit?.signal?.aborted).toBe(true);
  });
});
