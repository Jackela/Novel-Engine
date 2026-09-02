import type { Dispatch, SetStateAction } from "react";
import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { job } from "@/test/factories";
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

const jobFixture = job();

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
    const results = [{ document_id: "document-1", title: "Chapter", excerpt: "Clockwork" }];
    vi.mocked(api.search).mockResolvedValue({ results });
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
    const results = [{ document_id: "document-1", title: "Chapter", excerpt: "Clockwork" }];
    vi.mocked(api.search).mockResolvedValue({ results });
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
    vi.mocked(api.search).mockResolvedValue({
      results: [{ document_id: "document-1", title: "Chapter", excerpt: "Clockwork" }],
    });
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

  it("loads jobs into observable hook state", async () => {
    // Given
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [jobFixture] });
    const harness = renderQueryHooks();

    // When
    await act(async () => {
      await harness.result().jobs.loadJobs();
    });

    // Then
    expect(harness.result().jobs.jobs).toEqual([jobFixture]);
    expect(harness.result().error).toBeNull();
  });

  it("coalesces duplicate jobs refreshes before pending state renders", async () => {
    const response = deferred<{ jobs: ReturnType<typeof job>[] }>();
    vi.mocked(api.jobs).mockReturnValue(response.promise);
    const harness = renderQueryHooks();
    let first!: Promise<void>;
    let duplicate!: Promise<void>;

    act(() => {
      first = harness.result().jobs.loadJobs("refresh");
      duplicate = harness.result().jobs.loadJobs("refresh");
    });

    expect(api.jobs).toHaveBeenCalledTimes(1);
    expect(duplicate).toBe(first);
    expect(harness.result().jobs.loadingInitiator).toBe("refresh");
    await act(async () => {
      response.resolve({ jobs: [jobFixture] });
      await first;
    });
    expect(harness.result().jobs.loadingInitiator).toBeNull();
  });

  it("starts a new non-coalesced proposal audit after cancelling an earlier jobs read", async () => {
    const earlier = deferred<{ jobs: ReturnType<typeof job>[] }>();
    const audit = deferred<{ jobs: ReturnType<typeof job>[] }>();
    vi.mocked(api.jobs).mockReturnValueOnce(earlier.promise).mockReturnValueOnce(audit.promise);
    const harness = renderQueryHooks();
    let earlierLoad: Promise<void> = Promise.resolve();
    let audited: Promise<boolean> = Promise.resolve(false);

    act(() => {
      earlierLoad = harness.result().jobs.loadJobs("refresh");
      audited = harness.result().jobs.auditProposalOutcome();
    });

    expect(api.jobs).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.jobs).mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    expect(harness.result().jobs.proposalAuditStatus).toBe("auditing");

    await act(async () => {
      earlier.resolve({ jobs: [] });
      audit.resolve({ jobs: [jobFixture] });
      await earlierLoad;
      await expect(audited).resolves.toBe(true);
    });

    expect(harness.result().jobs.jobs).toEqual([jobFixture]);
    expect(harness.result().jobs.proposalAuditStatus).toBe("audit_succeeded");
  });

  it("keeps an unknown proposal gated when its non-coalesced audit read fails", async () => {
    vi.mocked(api.jobs).mockRejectedValue(new Error("audit unavailable"));
    const harness = renderQueryHooks();
    let audited: Promise<boolean> = Promise.resolve(true);

    act(() => {
      audited = harness.result().jobs.auditProposalOutcome();
    });

    await act(async () => {
      await expect(audited).resolves.toBe(false);
    });

    expect(harness.result().jobs.proposalAuditStatus).toBe("audit_failed");
    expect(harness.result().error).toBeNull();
  });

  it("clears a stale error when a later jobs refresh succeeds", async () => {
    // Given
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [jobFixture] });
    const harness = renderQueryHooks();
    act(() => {
      harness.result().setError("Previous jobs refresh failed.");
    });

    // When
    await act(async () => {
      await harness.result().jobs.loadJobs();
    });

    // Then
    expect(harness.result().jobs.jobs).toEqual([jobFixture]);
    expect(harness.result().error).toBeNull();
  });

  it("reports a jobs loading failure", async () => {
    // Given
    vi.mocked(api.jobs).mockRejectedValue(new Error("jobs unavailable"));
    const harness = renderQueryHooks();

    // When
    await act(async () => {
      await harness.result().jobs.loadJobs();
    });

    // Then
    expect(harness.result().jobs.jobs).toEqual([]);
    expect(harness.result().error).toBe("jobs unavailable");
  });

  it("hides project-scoped jobs and search state immediately when the project changes", async () => {
    // Given
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [jobFixture] });
    vi.mocked(api.search).mockResolvedValue({
      results: [{ document_id: "document-1", title: "Chapter", excerpt: "Clockwork" }],
    });
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

  it("aborts previous-project jobs and discards their reverse-order completion", async () => {
    // Given
    const firstRequest = deferred<{ jobs: ReturnType<typeof job>[] }>();
    const secondJob = job({ id: "job-project-2", project_id: "project-2" });
    vi.mocked(api.jobs)
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce({ jobs: [secondJob] });
    const harness = renderQueryHooks("project-1");
    let firstLoad: Promise<void> | undefined;
    act(() => {
      firstLoad = harness.result().jobs.loadJobs();
    });

    // When
    harness.rerender("project-2");
    await act(async () => {
      await harness.result().jobs.loadJobs();
    });
    const firstSignal = vi.mocked(api.jobs).mock.calls[0]?.[1]?.signal;
    await act(async () => {
      firstRequest.resolve({ jobs: [jobFixture] });
      await firstRequest.promise;
      await firstLoad;
      await Promise.resolve();
    });

    // Then
    expect(firstSignal?.aborted).toBe(true);
    expect(harness.result().jobs.jobs).toEqual([secondJob]);
    expect(harness.result().error).toBeNull();
  });

  it("aborts an earlier search and keeps only the latest project's results", async () => {
    // Given
    const firstRequest = deferred<{
      results: { document_id: string; title: string; excerpt: string }[];
    }>();
    const secondResults = [
      { document_id: "document-2", title: "Second", excerpt: "Second project" },
    ];
    vi.mocked(api.search)
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce({ results: secondResults });
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
      firstRequest.resolve({
        results: [{ document_id: "document-1", title: "First", excerpt: "First project" }],
      });
      await firstRequest.promise;
      await flushEffects();
    });

    // Then
    expect(firstSignal?.aborted).toBe(true);
    expect(harness.result().search.searchResults).toEqual(secondResults);
    expect(harness.result().error).toBeNull();
  });
});
