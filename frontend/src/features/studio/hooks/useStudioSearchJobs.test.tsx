import type { Dispatch, SetStateAction } from "react";
import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { jobSummary } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { useStudioJobs } from "./useStudioJobs";
import { useStudioSearch } from "./useStudioSearch";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      jobs: vi.fn<typeof actual.api.jobs>(),
      search: vi.fn<typeof actual.api.search>(),
    },
  };
});

interface HarnessSnapshot {
  readonly jobs: ReturnType<typeof useStudioJobs>;
  readonly search: ReturnType<typeof useStudioSearch>;
  readonly error: string | null;
  readonly setError: Dispatch<SetStateAction<string | null>>;
}

type SearchHit = { document_id: string; title: string; excerpt: string; match_term: string };
type SearchPage = { results: SearchHit[]; total: number; next_offset: number | null };

/** DR-029: one search-hit fixture with its locate term. */
function hit(document_id: string, title: string, excerpt: string): SearchHit {
  return { document_id, title, excerpt, match_term: title.toLowerCase() };
}

function page(results: SearchHit[], next_offset: number | null = null): SearchPage {
  return { results, total: results.length, next_offset };
}

const jobFixture = jobSummary();

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderQueryHooks(initialProjectId = "project-1"): {
  readonly result: () => HarnessSnapshot;
  readonly submitSearch: () => void;
  readonly rerender: (projectId: string) => void;
} {
  let projectId = initialProjectId;
  let current: HarnessSnapshot | undefined;

  function Wrapper() {
    const [error, setError] = useState<string | null>(null);
    const jobs = useStudioJobs(projectId, setError);
    const search = useStudioSearch(projectId, setError);
    current = { jobs, search, error, setError };
    return <form onSubmit={search.runSearch} />;
  }

  const { container, root } = harness.mount(<Wrapper />);
  const form = container.querySelector("form");
  if (form === null) {
    throw new Error("Expected search form after render.");
  }

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected query hook result after render.");
      }
      return current;
    },
    submitSearch: () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    },
    rerender: (nextProjectId: string) => {
      projectId = nextProjectId;
      act(() => root.render(<Wrapper />));
    },
  };
}

describe("Studio query hooks", () => {
  it("publishes search results and returns to the idle state", async () => {
    // Given
    const results = [hit("document-1", "Chapter", "Clockwork")];
    vi.mocked(api.search).mockResolvedValue(page(results));
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch("clockwork");
    });

    // When
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().search.searchResults).toEqual(results);
    expect(harness.result().search.isSearching).toBe(false);
    expect(harness.result().error).toBeNull();
  });

  it("clears a stale error when a later search succeeds", async () => {
    // Given
    const results = [hit("document-1", "Chapter", "Clockwork")];
    vi.mocked(api.search).mockResolvedValue(page(results));
    const harness = renderQueryHooks();
    act(() => {
      harness.result().setError("Previous search failed.");
      harness.result().search.setSearch("clockwork");
    });

    // When
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().search.searchResults).toEqual(results);
    expect(harness.result().error).toBeNull();
  });

  it("applies consecutive setSearch updates against the latest value", () => {
    // Given
    const harness = renderQueryHooks();

    // When: both updates land in one batch, before any re-render commits.
    act(() => {
      harness.result().search.setSearch("clock");
      harness.result().search.setSearch((current) => `${current}-work`);
    });

    // Then: the functional update sees "clock", not the initial "".
    expect(harness.result().search.search).toBe("clock-work");
  });

  it("skips whitespace-only searches and clears prior results", async () => {
    // Given
    vi.mocked(api.search).mockResolvedValue(page([hit("document-1", "Chapter", "Clockwork")]));
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch("clockwork");
    });
    await act(async () => {
      harness.submitSearch();
    });

    // When
    act(() => {
      harness.result().search.setSearch("   ");
    });
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().search.searchResults).toEqual([]);
    expect(api.search).toHaveBeenCalledTimes(1);
  });

  it("reports a search failure and resets the searching state", async () => {
    // Given
    vi.mocked(api.search).mockRejectedValue(new Error("search unavailable"));
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch("clockwork");
    });

    // When
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().error).toBe("search unavailable");
    expect(harness.result().search.isSearching).toBe(false);
  });

  it("hides project-scoped jobs and search state immediately when the project changes", async () => {
    // Given
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [jobFixture], next_cursor: null });
    vi.mocked(api.search).mockResolvedValue(page([hit("document-1", "Chapter", "Clockwork")]));
    const harness = renderQueryHooks("project-1");
    await act(async () => {
      await harness.result().jobs.loadJobs();
      harness.result().search.setSearch("clockwork");
      harness.submitSearch();
      await Promise.resolve();
    });

    // When
    harness.rerender("project-2");

    // Then
    expect(harness.result().jobs.jobs).toEqual([]);
    expect(harness.result().jobs.isLoading).toBe(false);
    expect(harness.result().search.search).toBe("");
    expect(harness.result().search.searchResults).toEqual([]);
    expect(harness.result().search.isSearching).toBe(false);
  });

  it("aborts an earlier search and keeps only the latest project's results", async () => {
    // Given
    const firstRequest = deferred<SearchPage>();
    const secondResults = [hit("document-2", "Second", "Second project")];
    vi.mocked(api.search)
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce(page(secondResults));
    const harness = renderQueryHooks("project-1");
    act(() => {
      harness.result().search.setSearch("first");
      harness.submitSearch();
    });

    // When
    harness.rerender("project-2");
    act(() => {
      harness.result().search.setSearch("second");
    });
    await act(async () => {
      harness.submitSearch();
    });
    const firstSignal = vi.mocked(api.search).mock.calls[0]?.[2]?.signal;
    await act(async () => {
      firstRequest.resolve(page([hit("document-1", "First", "First project")]));
      await firstRequest.promise;
      await flushEffects();
    });

    // Then
    expect(firstSignal?.aborted).toBe(true);
    expect(harness.result().search.searchResults).toEqual(secondResults);
    expect(harness.result().error).toBeNull();
  });

  it("pages beyond the first page with the server's next offset (DR-029)", async () => {
    // Given
    const firstPage = [hit("document-1", "One", "willowquill one")];
    const secondPage = [hit("document-2", "Two", "willowquill two")];
    vi.mocked(api.search)
      .mockResolvedValueOnce({ results: firstPage, total: 2, next_offset: 30 })
      .mockResolvedValueOnce({ results: secondPage, total: 2, next_offset: null });
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch("willowquill");
    });
    await act(async () => {
      harness.submitSearch();
    });

    // Then: the first page advertises the walk and no zero-result hint.
    expect(harness.result().search.searchResults).toEqual(firstPage);
    expect(harness.result().search.searchTotal).toBe(2);
    expect(harness.result().search.hasMoreResults).toBe(true);
    expect(harness.result().search.searchedEmpty).toBe(false);

    // When
    await act(async () => {
      await harness.result().search.loadMoreResults();
    });

    // Then: the second page appends in order and closes the walk.
    expect(vi.mocked(api.search).mock.calls[1]?.[0]).toBe("project-1");
    expect(vi.mocked(api.search).mock.calls[1]?.[1]).toBe("willowquill");
    expect(vi.mocked(api.search).mock.calls[1]?.[2]?.offset).toBe(30);
    expect(harness.result().search.searchResults).toEqual([...firstPage, ...secondPage]);
    expect(harness.result().search.hasMoreResults).toBe(false);
    expect(harness.result().error).toBeNull();
  });

  it("marks only a completed empty search as the zero-result state (DR-029)", async () => {
    // Given
    vi.mocked(api.search).mockResolvedValue({ results: [], total: 0, next_offset: null });
    const harness = renderQueryHooks();
    act(() => {
      harness.result().search.setSearch("nothing here");
    });

    // When
    await act(async () => {
      harness.submitSearch();
    });

    // Then
    expect(harness.result().search.searchedEmpty).toBe(true);

    // When the input changes after the search, the stale hint must vanish.
    act(() => {
      harness.result().search.setSearch("nothing here yet");
    });
    expect(harness.result().search.searchedEmpty).toBe(false);
  });
});
