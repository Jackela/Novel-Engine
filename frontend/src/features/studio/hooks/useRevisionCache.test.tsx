import { act, StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RevisionPage } from "@/app/types/studio";
import { revision } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { resetRevisionCacheForTests, useRevisionCache } from "./useRevisionCache";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      revisions: vi.fn<typeof actual.api.revisions>(),
    },
  };
});

type HookResult = ReturnType<typeof useRevisionCache>;

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  vi.resetAllMocks();
});

const revisionOne = revision("revision-1");
const staleRevision = revision("revision-stale", {
  source: "restore",
});

function renderCache(): {
  readonly result: () => { readonly hook: HookResult };
  readonly onError: ReturnType<typeof vi.fn>;
  readonly rerender: (projectId: string, documentId: string) => void;
  readonly dispose: () => void;
} {
  let projectId = "project-1";
  let documentId = "document-1";
  let current: { readonly hook: HookResult } | undefined;
  const onError = vi.fn();

  function Wrapper(): null {
    current = { hook: useRevisionCache(projectId, documentId, onError) };
    return null;
  }

  const { container, root } = harness.mount(<Wrapper />);

  return {
    result: () => {
      if (current === undefined) throw new Error("Expected hook result after render.");
      return current;
    },
    onError,
    rerender: (nextProjectId, nextDocumentId) => {
      projectId = nextProjectId;
      documentId = nextDocumentId;
      act(() => root.render(<Wrapper />));
    },
    dispose: () => {
      harness.unmount(container);
    },
  };
}

function renderStrictCache(): { readonly result: () => HookResult } {
  let current: HookResult | undefined;
  const onError = vi.fn();

  function Wrapper(): null {
    current = useRevisionCache("project-1", "document-1", onError);
    return null;
  }

  harness.mount(
    <StrictMode>
      <Wrapper />
    </StrictMode>,
  );

  return {
    result: () => {
      if (current === undefined) throw new Error("Expected hook result after render.");
      return current;
    },
  };
}

describe("useRevisionCache", () => {
  it("aborts requests on document change, project change, and unmount", async () => {
    vi.mocked(api.revisions).mockReturnValue(new Promise(() => {}));
    const cache = renderCache();
    const documentOneInit = vi.mocked(api.revisions).mock.calls[0]?.[2];

    cache.rerender("project-1", "document-2");
    await flushEffects();

    expect(documentOneInit?.signal?.aborted).toBe(true);
    const projectOneInit = vi.mocked(api.revisions).mock.calls[1]?.[2];
    expect(projectOneInit?.signal?.aborted).toBe(false);

    cache.rerender("project-2", "document-2");
    await flushEffects();

    expect(projectOneInit?.signal?.aborted).toBe(true);
    const projectTwoInit = vi.mocked(api.revisions).mock.calls[2]?.[2];
    expect(projectTwoInit?.signal?.aborted).toBe(false);

    cache.dispose();
    expect(projectTwoInit?.signal?.aborted).toBe(true);
  });

  it("cancels an older same-owner refresh and ignores its aborted failure", async () => {
    const firstRequest = deferred<RevisionPage>();
    let rejectFirst: ((reason: unknown) => void) | undefined;
    const abortableFirst = new Promise<RevisionPage>((resolve, reject) => {
      rejectFirst = reject;
      void firstRequest.promise.then(resolve);
    });
    vi.mocked(api.revisions)
      .mockReturnValueOnce(abortableFirst)
      .mockResolvedValueOnce({ revisions: [revisionOne], next_cursor: null });
    const cache = renderCache();
    const firstInit = vi.mocked(api.revisions).mock.calls[0]?.[2];

    await act(async () => {
      await cache.result().hook.refreshDocumentRevisions("document-1");
    });
    rejectFirst?.(new DOMException("cancelled", "AbortError"));
    await flushEffects();

    expect(firstInit?.signal?.aborted).toBe(true);
    expect(cache.onError).not.toHaveBeenCalled();
    expect(cache.result().hook.revisions).toEqual([revisionOne]);
  });

  it("restarts the owner load after StrictMode aborts the simulated mount", async () => {
    const firstRequest = deferred<RevisionPage>();
    vi.mocked(api.revisions)
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce({ revisions: [revisionOne], next_cursor: null });

    const cache = renderStrictCache();
    await flushEffects();

    expect(api.revisions).toHaveBeenCalledTimes(2);
    const firstInit = vi.mocked(api.revisions).mock.calls[0]?.[2];
    expect(firstInit?.signal?.aborted).toBe(true);
    expect(cache.result().revisions).toEqual([revisionOne]);
  });

  it("resolves refresh after the latest revision response updates the cache", async () => {
    let resolveResponse: ((response: RevisionPage) => void) | undefined;
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [], next_cursor: null })
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveResponse = resolve;
        }),
      );
    const cache = renderCache();

    let settled = false;
    const refresh = cache.result().hook.refreshDocumentRevisions("document-1");
    refresh.then(() => {
      settled = true;
    });

    await act(async () => {
      await Promise.resolve();
    });
    expect(settled).toBe(false);

    await act(async () => {
      resolveResponse?.({ revisions: [revisionOne], next_cursor: null });
      await refresh;
      await Promise.resolve();
    });

    expect(settled).toBe(true);
    expect(cache.result().hook.revisions).toEqual([revisionOne]);
  });

  it("does not let an unmounted cache instance overwrite a newer response", async () => {
    let resolveStale: ((response: RevisionPage) => void) | undefined;
    let resolveCurrent: ((response: RevisionPage) => void) | undefined;
    vi.mocked(api.revisions)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveStale = resolve;
        }),
      )
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveCurrent = resolve;
        }),
      );

    const staleCache = renderCache();
    staleCache.dispose();
    const currentCache = renderCache();

    await act(async () => {
      resolveCurrent?.({ revisions: [revisionOne], next_cursor: null });
      await Promise.resolve();
    });
    await act(async () => {
      resolveStale?.({ revisions: [staleRevision], next_cursor: null });
      await Promise.resolve();
    });

    expect(currentCache.result().hook.revisions).toEqual([revisionOne]);
  });

  it("does not publish a late revision error after the project owner changes", async () => {
    let rejectStale: ((reason: unknown) => void) | undefined;
    const projectTwoRevision = revision("project-2-revision", {
      document_id: "document-1",
      source: "restore",
    });
    vi.mocked(api.revisions)
      .mockReturnValueOnce(
        new Promise((_resolve, reject) => {
          rejectStale = reject;
        }),
      )
      .mockResolvedValueOnce({ revisions: [projectTwoRevision], next_cursor: null });
    const cache = renderCache();

    cache.rerender("project-2", "document-1");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(cache.result().hook.revisions).toEqual([projectTwoRevision]);

    await act(async () => {
      rejectStale?.(new Error("late project one revisions failure"));
      await Promise.resolve();
    });

    expect(cache.onError).not.toHaveBeenCalled();
    expect(cache.result().hook.revisions).toEqual([projectTwoRevision]);
  });
});
